/* Appended to the private renderer source to access its static draw entry.
   Only this fixture/vtable is added; the timed production functions are intact. */
#include "calibration.h"
static SWRenderer calibration_renderer;
static DataWin calibration_data;
static Sprite calibration_sprites[43];
static TexturePageItem calibration_item;
static int32_t calibration_tpag_index;
static SWTexture calibration_texture;
static SWTexture *calibration_pages[1],*calibration_items[1];
static uintpixel_t calibration_fb[320*240] __attribute__((aligned(4096)));
static uintpixel_t calibration_texels[40*40],calibration_half[20*20];
static uint8_t calibration_coverage[20*20];
static uint16_t calibration_bounds[40],calibration_full_bounds[40];
static RendererVtable calibration_vtable={.drawSprite=SWRenderer_drawSprite};
extern void calibration_pack_init(void);
void calibration_sprite_setup(void){
 SWRenderer *s=&calibration_renderer;
 s->base.dataWin=&calibration_data;s->base.vtable=&calibration_vtable;s->base.drawAlpha=1.0f;
 s->width=s->mainWidth=s->fbPitch=s->mainPitch=320;s->height=s->mainHeight=240;
 s->fb=s->mainFb=calibration_fb;s->viewW=s->portW=s->gameW=s->maxX=320;
 s->viewH=s->portH=s->gameH=s->maxY=240;s->scaleX=s->scaleY=0.5f;s->writeMask=WRITE_MASK_ALL;
 s->totalTextureCount=s->textureCount=s->originalTPagCount=s->itemCount=1;
 s->textures=calibration_pages;s->itemTextures=calibration_items;
 calibration_items[0]=&calibration_texture;s->frameCounter=3323;
 calibration_data.sprt.count=43;calibration_data.sprt.sprites=calibration_sprites;
 calibration_data.tpag.count=1;calibration_data.tpag.items=&calibration_item;
 Sprite *sp=&calibration_sprites[42];sp->width=sp->height=40;sp->textureCount=1;sp->tpagIndices=&calibration_tpag_index;
 calibration_item.sourceWidth=calibration_item.sourceHeight=calibration_item.targetWidth=calibration_item.targetHeight=40;
 calibration_item.boundingWidth=calibration_item.boundingHeight=40;
 calibration_texture.width=calibration_texture.height=40;calibration_texture.buffer=calibration_texels;
 calibration_texture.halfBuffer=calibration_half;calibration_texture.halfCoverage=calibration_coverage;
 calibration_texture.halfRowBounds=calibration_bounds;calibration_texture.halfFullBounds=calibration_full_bounds;
 calibration_texture.immutable=true;calibration_texture.solid=calibration_texture.halfSolid=2;
 for(unsigned y=0;y<20;y++){
  calibration_bounds[y*2]=0;calibration_bounds[y*2+1]=20;
  calibration_full_bounds[y*2]=1;calibration_full_bounds[y*2+1]=20;
  for(unsigned x=0;x<20;x++){
   uintpixel_t color=x?0x8000u|((x&31)<<10)|((y&31)<<5)|((x+y)&31):0x8000u;
   calibration_half[y*20+x]=color;calibration_coverage[y*20+x]=x?4:1;
   for(unsigned oy=0;oy<2;oy++)for(unsigned ox=0;ox<2;ox++)
    calibration_texels[(y*2+oy)*40+x*2+ox]=(x || (ox==0 && oy==0))?color:0;
  }
 }
 for(unsigned i=0;i<320*240;i++)calibration_fb[i]=0x8000;
 swrFavorSpeed=true;swrSkipFrame=false;swrProbing=true;swrDrawTimed=false;swrCallNotes=false;
 calibration_pack_init();
}
void calibration_sprite_warm(void){
 swrProbeStop=0;swrProbePath=0;
 Renderer_drawSprite(&calibration_renderer.base,42,0,60.0f,60.0f);
 swrOverlayFlush(&calibration_renderer);
}
void calibration_sprite_stage(unsigned stage){swrProbeStop=stage==7?0:(int)stage;}
__attribute__((noinline)) uint32_t calibration_sprite_draw(uint32_t n,void *arg){
 SWRenderer *s=&calibration_renderer;float y=(float)s->viewY+60.0f;
 if((uintptr_t)arg==7){for(unsigned i=0;i<n;i++)Renderer_drawSprite(&s->base,42,0,(float)s->viewX-10000.0f,y);}
 else {float x=(float)s->viewX+60.0f;for(unsigned i=0;i<n;i++)Renderer_drawSprite(&s->base,42,0,x,y);}
 return swrProbePath;
}
uint32_t calibration_sprite_check(void){
 if(swrProbePath!=1 || calibration_renderer.overlayCount || calibration_renderer.mirrorLayers)
  calibration_fail("sprite path or pending layers");
 uint32_t hash=2166136261u;
 for(unsigned y=0;y<240;y++)for(unsigned x=0;x<320;x++){
  uintpixel_t expected=0x8000;
  if(x>=31 && x<50 && y>=30 && y<50){unsigned sx=x-30,sy=y-30;expected=0x8000u|(sx<<10)|(sy<<5)|((sx+sy)&31);}
  uintpixel_t pixel=calibration_fb[y*320+x];
  if(pixel!=expected)calibration_fail("independent sprite pixel oracle");
  hash=(hash^(pixel&255))*16777619u;hash=(hash^(pixel>>8))*16777619u;
 }
 return hash;
}
