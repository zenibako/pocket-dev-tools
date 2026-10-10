// Passive companion to CacheMonitor. Bits retain overlaps instead of summing
// independently observed causes as if they were mutually exclusive lost cycles.
struct PipelineInstruction { uint32_t pc=0,uop=0; bool valid=false; };
struct PipelineFrame {
    std::map<uint32_t,uint64_t> masks;
    std::map<std::pair<uint32_t,uint32_t>,uint64_t> blocked,retired;
};
class PipelineMonitor {
    std::array<PipelineInstruction,65536> instructions{};
    std::vector<PipelineFrame> frames;
    bool recovering=false;
    uint32_t target=0,branch_pc=0;
    uint64_t redirect=0;
public:
    template<class T> void sample(const T& p,bool active,size_t index,bool i,bool d,std::ofstream& out) {
        if(p.cp_rs != p.cp_rs_reconstructed)
            throw std::runtime_error("producer hazard reconstruction disagrees with RTL at cycle "+std::to_string(p.cp_counter));
        bool freeze=p.cp_div_freeze||p.cp_sqrt||p.cp_f2i||p.cp_i2f||p.cp_io||p.cp_csr||p.cp_atomic;
        if(freeze!=bool(p.cp_freeze))throw std::runtime_error("unaccounted execute freeze source");
        bool blocked=p.cp_candidate&&!p.cp_dispatch;
        uint32_t mask=0;
        auto bit=[&](unsigned n,bool value){if(value)mask|=uint32_t(1)<<n;};
        bit(0,p.cp_retire);bit(1,p.cp_dispatch);bit(2,p.cp_candidate);bit(3,p.cp_freeze);
        bit(4,i);bit(5,d);bit(6,blocked&&p.cp_rs);bit(7,blocked&&p.cp_load_dep);
        bit(8,blocked&&p.cp_mul_dep);bit(9,blocked&&p.cp_fp_dep);
        bit(10,blocked&&p.cp_reservation);bit(11,blocked&&p.cp_flush_hazard);
        bit(12,blocked&&p.cp_fence);bit(13,p.cp_store_wait);
        bit(14,p.cp_div_freeze&&!p.cp_fp_div);bit(15,p.cp_div_freeze&&p.cp_fp_div);
        bit(16,p.cp_sqrt);bit(17,p.cp_f2i);bit(18,p.cp_i2f);bit(19,p.cp_io);
        bit(20,p.cp_csr);bit(21,p.cp_atomic);bit(22,recovering);
        bit(23,p.cp_branch);bit(24,p.cp_branch&&p.cp_branch_wrong);
        bit(25,p.cp_btb);bit(26,p.cp_decode_redirect);
        if(active){
            if(frames.size()<=index)frames.resize(index+1);
            auto& f=frames[index];f.masks[mask]++;
            if(blocked)f.blocked[{p.cp_dispatch_pc,mask}]++;
            if(p.cp_retire){
                auto& ins=instructions[p.cp_retire_id];
                if(!ins.valid)throw std::runtime_error("retirement without observed dispatch");
                f.retired[{ins.pc,ins.uop}]++;
            }
        }
        // Track UOP IDs from dispatch through canonical architectural retirement.
        // Cancellations never retire. Wrapping 16-bit IDs exceed pipeline depth.
        if(p.cp_retire)instructions[p.cp_retire_id].valid=false;
        if(p.cp_dispatch)instructions[p.cp_dispatch_id]={p.cp_dispatch_pc,p.cp_dispatch_uop,true};
        if(recovering&&p.cp_dispatch&&p.cp_dispatch_pc==target){
            out<<"B,"<<branch_pc<<','<<redirect<<','<<p.cp_counter<<'\n';recovering=false;
        }
        if(p.cp_branch&&p.cp_branch_wrong){
            if(recovering)throw std::runtime_error("branch redirected before recovery target dispatched");
            recovering=true;target=p.cp_branch_target;branch_pc=p.cp_branch_pc;redirect=p.cp_counter;
        }
    }
    void finish(std::ofstream& out){
        for(size_t index=0;index<frames.size();index++){
            auto& f=frames[index];
            for(auto& m:f.masks)out<<"P,"<<index<<','<<m.first<<','<<m.second<<'\n';
            for(auto& h:f.blocked)out<<"S,"<<index<<','<<h.first.first<<','<<h.first.second<<','<<h.second<<'\n';
            for(auto& h:f.retired)out<<"T,"<<index<<','<<h.first.first<<','<<h.first.second<<','<<h.second<<'\n';
        }
        if(recovering)out<<"V,"<<branch_pc<<','<<redirect<<",0\n";
    }
};
