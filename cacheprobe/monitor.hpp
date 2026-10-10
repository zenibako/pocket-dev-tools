// Sample only settled, pre-rising-edge signals. This observer never drives RTL.
#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "pipeline.hpp"

struct CacheTransfer {
    bool offered=false, accepted=false;
    uint32_t address=0, length=0, beats=0;
    uint64_t offer=0, accept=0, first=0;
};
struct CacheFrame {
    uint64_t begin=0, end=0, samples=0, i_hold=0, d_wait=0, overlap=0;
    uint64_t fetch_hold=0, miss_wait=0, miss_events=0;
    uint64_t i_no_commit=0, d_no_commit=0, overlap_no_commit=0, commits=0;
    // Blocked fetch PC, rather than charging a speculative refill's latency
    // to a function that may never execute.
    std::map<uint32_t,std::array<uint64_t,2>> holds;
};
class CacheMonitor {
    bool enabled=false, active=false, clock_pending=false, i_waiting=false;
    uint32_t i_wait_pc=0;
    uint64_t i_miss_cycle=0;
    uint32_t begin_lo=0,begin_hi=0,end_lo=0,end_hi=0,clock_pc=0;
    std::array<CacheTransfer,4> instructions{}, data{};
    std::vector<CacheFrame> frames;
    std::ofstream output;
    PipelineMonitor pipeline;
    static uint32_t setting(const char* name) {
        const char* s=std::getenv(name);
        if(!s)throw std::runtime_error(std::string("missing cache observer setting ")+name);
        return std::strtoul(s,nullptr,0);
    }
    void transfer(char kind, std::array<CacheTransfer,4>& slots,uint64_t cycle,
                  bool arv,bool arr,uint32_t addr,unsigned aid,unsigned length,
                  bool rv,bool rr,unsigned rid,bool last,unsigned response) {
        // Process a finishing transfer before a possible reuse of the same ID.
        if(rv && rr) {
            if(rid>=slots.size() || !slots[rid].accepted || response)
                throw std::runtime_error("cache refill response without matching accepted ID, or AXI error");
            auto& t=slots[rid];
            if(t.beats++==0)t.first=cycle;
            if(last) {
                if(t.beats!=t.length+1)throw std::runtime_error("cache refill beat/RLAST mismatch");
                output<<"R,"<<kind<<','<<t.address<<','<<rid<<','<<t.offer<<','
                      <<t.accept<<','<<t.first<<','<<cycle<<','<<t.beats<<'\n';
                t=CacheTransfer{};
            } else if(t.beats>=t.length+1)throw std::runtime_error("cache refill missing RLAST");
        }
        if(arv) {
            if(aid>=slots.size())throw std::runtime_error("invalid cache refill ID");
            auto& t=slots[aid];
            if(!t.offered) {
                if(t.accepted)throw std::runtime_error("cache refill ID reused while outstanding");
                t.offered=true;t.offer=cycle;t.address=addr;t.length=length;
            } else if(t.accepted || t.address!=addr || t.length!=length)
                throw std::runtime_error("unstable cache refill offer");
            if(arr){t.accepted=true;t.accept=cycle;}
        }
    }
public:
    void init() {
        enabled=std::getenv("CACHE_PROFILE") && std::atoi(std::getenv("CACHE_PROFILE"));
        if(!enabled)return;
        begin_lo=setting("CACHE_BEGIN_LO");begin_hi=setting("CACHE_BEGIN_HI");
        end_lo=setting("CACHE_END_LO");end_hi=setting("CACHE_END_HI");
        output.open("cache-profile.csv");
        if(!output)throw std::runtime_error("cannot open cache profile");
        output<<"# os25 passive cache observer v3; timestamps are the MMIO counter\n";
    }
    template<class T> void sample(const T& tb) {
        if(!enabled)return;
        uint64_t cycle=tb.cp_counter;
        if(tb.cp_clock_cmd) {
            if(clock_pending)throw std::runtime_error("overlapping MMIO clock requests");
            clock_pending=true;clock_pc=tb.cp_clock_pc;
        }
        if(tb.cp_clock_latch) {
            if(!clock_pending)throw std::runtime_error("MMIO clock latch without a CPU request");
            clock_pending=false;
            if(clock_pc>=begin_lo && clock_pc<begin_hi) {
                if(active)throw std::runtime_error("nested cache profile frame");
                frames.emplace_back();frames.back().begin=cycle;active=true;
            } else if(clock_pc>=end_lo && clock_pc<end_hi) {
                if(!active)throw std::runtime_error("cache profile end without begin");
                frames.back().end=cycle;active=false;
            }
        }
        transfer('I',instructions,cycle,tb.cp_i_arvalid,tb.cp_i_arready,tb.cp_i_araddr,
                 tb.cp_i_arid,tb.cp_i_arlen,tb.cp_i_rvalid,tb.cp_i_rready,
                 tb.cp_i_rid,tb.cp_i_rlast,tb.cp_i_rresp);
        transfer('D',data,cycle,tb.cp_d_arvalid,tb.cp_d_arready,tb.cp_d_araddr,
                 tb.cp_d_arid,tb.cp_d_arlen,tb.cp_d_rvalid,tb.cp_d_rready,
                 tb.cp_d_rid,tb.cp_d_rlast,tb.cp_d_rresp);
        pipeline.sample(tb,active,frames.empty()?0:frames.size()-1,tb.cp_i_hold||i_waiting,tb.cp_d_wait,output);
        if(active) {
            auto& f=frames.back();f.samples++;
            bool i=tb.cp_i_hold || i_waiting,d=tb.cp_d_wait,n=!tb.cp_commit;
            f.fetch_hold+=tb.cp_i_hold;f.miss_wait+=i_waiting;f.miss_events+=tb.cp_i_miss;
            f.i_hold+=i;f.d_wait+=d;f.overlap+=i&&d;
            f.i_no_commit+=i&&n;f.d_no_commit+=d&&n;f.overlap_no_commit+=i&&d&&n;
            f.commits+=!n;
            if(i){auto& h=f.holds[i_waiting ? i_wait_pc : tb.cp_i_pc];h[0]++;h[1]+=n;}
        }
        // Same edge and set-over-clear priority as the optional RTL event register.
        // Count the old register value above; publish an episode only on recovery.
        if(tb.cp_i_resume && i_waiting && !tb.cp_i_miss) {
            output<<"M,"<<i_wait_pc<<','<<i_miss_cycle<<','<<cycle<<'\n';
            i_waiting=false;
        }
        if(tb.cp_i_miss && !i_waiting) {
            i_waiting=true;i_wait_pc=tb.cp_i_miss_pc;i_miss_cycle=cycle;
        }
    }
    void finish() {
        if(!enabled)return;
        if(active)throw std::runtime_error("unfinished cache profile frame");
        for(size_t i=0;i<frames.size();i++) {
            auto& f=frames[i];
            if(f.samples!=f.end-f.begin)throw std::runtime_error("cache interval does not match MMIO elapsed cycles");
            output<<"F,"<<i<<','<<f.begin<<','<<f.end<<','<<f.samples<<','<<f.i_hold
                  <<','<<f.d_wait<<','<<f.overlap<<','<<f.i_no_commit<<','<<f.d_no_commit
                  <<','<<f.overlap_no_commit<<','<<f.commits<<','<<f.fetch_hold<<','<<f.miss_wait<<','<<f.miss_events<<'\n';
            for(auto& h:f.holds)output<<"H,"<<i<<','<<h.first<<','<<h.second[0]<<','<<h.second[1]<<'\n';
        }
        if(i_waiting)output<<"W,"<<i_wait_pc<<','<<i_miss_cycle<<','<<0<<'\n';
        for(auto kind:{'I','D'}) {
            auto& slots=kind=='I'?instructions:data;
            for(unsigned id=0;id<slots.size();id++)if(slots[id].offered) {
                auto& t=slots[id];output<<"U,"<<kind<<','<<t.address<<','<<id<<','
                    <<t.offer<<','<<t.accept<<','<<t.first<<','<<0<<','<<t.beats<<'\n';
            }
        }
        pipeline.finish(output);
        output.close();
    }
};
