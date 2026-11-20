// r6 exhaustive search: does a pivot walk of <= LT toggles exist in F2^6 (bits p=1,y1=2,y2=4,y3=8,e=16,a=32),
// generators {1,2,4,8,16,32,48}, start and end in {0,16}, whose visited set U admits an exact Walsh solution
// (g in span of chi_x, x in U, on the 37 labels)?
// Decomposition: Q5 = coordinates (low4, a); e is the only coordinate not in Q5.  Every move is either a Q5 move
// (1,2,4,8 or a; the a-move may carry an e flip: 32 vs 48) or an e-move (16).  Start/end in {0,16} => the Q5 walk
// is closed at 0, so its length m is even, and it must visit all 16 antipodal classes (cocircuits) => m >= 16.
// Phase 1: all closed Q5 walks of length m <= LT (even) covering all classes, pruned by an exact class-cover DP and by
// feasibility of the e-independent labels (labels with e-bit 0 see only the Q5 projection) on a reachable superset.
// Phase 2: every e-lift with e-budget k = LT - m: start e, a/a+e choice per a-move, at each position pure/flip/spur
// (spur = e-move out and back, cost 2; >= 3 e-moves at one position are dominated), pruned by superset feasibility.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
int NL; int lab[64]; double gv[64];
int NL0; int lab0[64]; double g0[64];
int LT; int SPLIT=0, NSPLIT=1; int NPRE=0, PRE[64];
unsigned char CD[32][65536];
static inline int clsq(int v){ return (v&15) ^ ((v>>4)&1 ? 15 : 0); }
static inline int pt(int v,int e){ return (v&15) | (e<<4) | (((v>>4)&1)<<5); }
// generic feasibility: is g (on labels lb) in span of chi_x for x in set (bitmask over 64 points)
static int feas_gen(uint64_t U, const int *lb, const double *gg, int nl){
  double Q[64][64]; int nb=0; double r[64]; memcpy(r,gg,sizeof(double)*nl);
  for(int x=0;x<64;x++) if(U>>x&1){
    double v[64]; for(int i=0;i<nl;i++) v[i]=(__builtin_popcount(lb[i]&x)&1)?-1.0:1.0;
    for(int rep=0;rep<2;rep++) for(int k=0;k<nb;k++){double d=0;for(int i=0;i<nl;i++)d+=Q[k][i]*v[i];for(int i=0;i<nl;i++)v[i]-=d*Q[k][i];}
    double nn=0;for(int i=0;i<nl;i++)nn+=v[i]*v[i]; nn=sqrt(nn);
    if(nn>1e-7){for(int i=0;i<nl;i++)Q[nb][i]=v[i]/nn; double d=0;for(int i=0;i<nl;i++)d+=Q[nb][i]*r[i];for(int i=0;i<nl;i++)r[i]-=d*Q[nb][i]; nb++;}
    if(nb==nl) break;
  }
  double s=0;for(int i=0;i<nl;i++)s+=r[i]*r[i]; return s<1e-10;
}

#define PMOD 2305843009213693951ULL
static inline uint64_t mulm(uint64_t a,uint64_t b){ __uint128_t z=(__uint128_t)a*b; uint64_t lo=(uint64_t)(z&PMOD), hi=(uint64_t)(z>>61); uint64_t r=lo+hi; if(r>=PMOD) r-=PMOD; return r; }
static uint64_t powm(uint64_t a,uint64_t e){ uint64_t r=1; while(e){ if(e&1) r=mulm(r,a); a=mulm(a,a); e>>=1;} return r; }
static int rankp(uint64_t M[64][66], int nl, int nc){ // rows nl, cols nc
  int r=0; for(int c=0;c<nc && r<nl;c++){ int piv=-1; for(int i=r;i<nl;i++) if(M[i][c]){piv=i;break;} if(piv<0) continue;
    if(piv!=r) for(int j=0;j<nc;j++){uint64_t t=M[r][j];M[r][j]=M[piv][j];M[piv][j]=t;}
    uint64_t inv=powm(M[r][c],PMOD-2);
    for(int i=0;i<nl;i++) if(i!=r && M[i][c]){ uint64_t f=mulm(M[i][c],inv); for(int j=c;j<nc;j++){ uint64_t t=mulm(f,M[r][j]); M[i][j]= M[i][j]>=t? M[i][j]-t : M[i][j]+PMOD-t; } }
    r++; }
  return r; }
static int feas_modp(uint64_t U,const int *lb,const double *gg,int nl){
  static uint64_t M[64][66]; int nc=0;
  for(int x=0;x<64;x++) if(U>>x&1){ for(int i=0;i<nl;i++) M[i][nc]=(__builtin_popcount(lb[i]&x)&1)?PMOD-1:1; nc++; }
  static uint64_t M2[64][66]; memcpy(M2,M,sizeof(M));
  int r1=rankp(M2,nl,nc);
  for(int i=0;i<nl;i++){ long long v=llround(gg[i]); M[i][nc]= v>=0? (uint64_t)v : PMOD-(uint64_t)(-v); }
  int r2=rankp(M,nl,nc+1); return r1==r2; }
long long nmis=0;
// caches
#define HB 23
uint64_t *HK1; unsigned char *HV1; uint64_t *HK2; unsigned char *HV2;
long long nfeas1=0,nfeas2=0;
static int feas_cached(uint64_t U,int full){
  uint64_t *HK= full?HK2:HK1; unsigned char *HV= full?HV2:HV1;
  uint64_t h=U*0x9E3779B97F4A7C15ULL; h^=h>>31; h&=(1ULL<<HB)-1;
  for(int t=0;t<8;t++){ uint64_t s=(h+t)&((1ULL<<HB)-1); if(HK[s]==U) return HV[s]; if(HK[s]==0) break; }
  int r= full? feas_gen(U,lab,gv,NL) : feas_gen(U,lab0,g0,NL0);
  if(full) nfeas2++; else nfeas1++;
#ifdef XCHECK
  { int r2= full? feas_modp(U,lab,gv,NL):feas_modp(U,lab0,g0,NL0); if(r2!=r){ nmis++; fprintf(stderr,"MISMATCH %016llx full=%d float=%d modp=%d\n",(unsigned long long)U,full,r,r2);} }
#endif
  for(int t=0;t<8;t++){ uint64_t s=(h+t)&((1ULL<<HB)-1); if(HK[s]==0||t==7){HK[s]=U;HV[s]=r;break;} }
  return r;
}
// Q5-set (32-bit over v) -> point set with e=0 (lab0 labels ignore e)
static inline uint64_t q2pts(uint32_t P){ uint64_t U=0; while(P){int v=__builtin_ctz(P); P&=P-1; U|=1ULL<<pt(v,0);} return U; }
int qw[64], qg[64]; // walk points and generator kinds (gen bit index 0..4; 4 = a-move)
long long n1=0, leaves1[64], n2=0, found=0;
uint64_t REST[64];
int M_cur, K_cur;
void dfs2(int i,int e,int b,uint64_t U){
  n2++;
  if(!feas_cached(U|REST[i],1)) return;
  int x0=pt(qw[i],e), x1=pt(qw[i],e^1);
  for(int opt=0;opt<3;opt++){
    int cost=opt; if(cost>b) break;
    uint64_t U2=U|(1ULL<<x0); if(opt) U2|=1ULL<<x1;
    int e2= (opt==1)? e^1 : e;
    if(i==M_cur){ if(opt==2) continue; if(feas_cached(U2,1)){ found++;
        printf("FOUND m=%d k=%d used=%d U=%016llx walk:",M_cur,K_cur,K_cur-(b-cost),(unsigned long long)U2);
        for(int j=0;j<=M_cur;j++) printf(" %d",qw[j]); printf("\n"); fflush(stdout);} continue; }
    if(qg[i]==4){ dfs2(i+1,e2,b-cost,U2); dfs2(i+1,e2^1,b-cost,U2); }
    else dfs2(i+1,e2,b-cost,U2);
  }
}
void phase2(int m){
  M_cur=m; K_cur=LT-m;
  REST[m+1]=0; for(int j=m;j>=0;j--) REST[j]=REST[j+1]|(1ULL<<pt(qw[j],0))|(1ULL<<pt(qw[j],1));
  for(int e0=0;e0<2;e0++) dfs2(0,e0,K_cur,0);
}
void dfs1(int d,int v,unsigned cm,uint32_t P,int last){
  n1++;
  int r=LT-d; // remaining Q5 moves allowed (upper bound)
  unsigned un=(~cm)&0xffff;
  if(CD[v][un]>r) return;
  if(d==3 && NSPLIT>1 && ((qg[0]*5+qg[1])*5+qg[2])%NSPLIT!=SPLIT) return;
  if(v==0 && un==0 && d>=16){ leaves1[d]++;
    if(feas_cached(q2pts(P),0)) { leaves1[d+32]++; phase2(d); if(found && getenv("STOPFIRST")){ printf("STOPFIRST n1=%lld\n",n1); exit(0);} } }
  if(r<=0) return;
  // superset check: points reachable and returnable within r
  { uint32_t R=P; for(int z=0;z<32;z++) if(__builtin_popcount(v^z)+__builtin_popcount(z)<=r) R|=1u<<z;
    if(!feas_cached(q2pts(R),0)) return; }
  for(int k=0;k<5;k++){ if(d<NPRE && k!=PRE[d]) continue; int nx=v^(1<<k); qg[d]=k; qw[d+1]=nx; dfs1(d+1,nx,cm|(1u<<clsq(nx)),P|(1u<<nx),k); }
}
int main(int argc,char**argv){
  LT=atoi(argv[1]); if(argc>3){SPLIT=atoi(argv[2]);NSPLIT=atoi(argv[3]);}
  FILE*f=fopen("lab.txt","r"); if(fscanf(f,"%d",&NL)!=1) return 1; for(int i=0;i<NL;i++) if(fscanf(f,"%d %lf",&lab[i],&gv[i])!=2) return 1; fclose(f);
  NL0=0; for(int i=0;i<NL;i++) if(!(lab[i]>>4&1)){lab0[NL0]=lab[i]; g0[NL0]=gv[i]; NL0++;}
  // class-cover DP
  for(int M=0;M<65536;M++) for(int v=0;v<32;v++){
    int Mp=M & ~(1<<clsq(v));
    if(Mp!=M){ CD[v][M]=CD[v][Mp]; continue; }
    if(M==0){ CD[v][M]=__builtin_popcount(v); continue; }
    int best=255; for(int w=0;w<32;w++){ int c=clsq(w); if(!(M>>c&1)) continue; int val=__builtin_popcount(v^w)+CD[w][M&~(1<<c)]; if(val<best) best=val; }
    CD[v][M]=best; }
  printf("NL=%d NL0=%d LT=%d split %d/%d CD[0][all-0]=%d\n",NL,NL0,LT,SPLIT,NSPLIT,CD[0][0xfffe]); fflush(stdout);
  HK1=calloc(1ULL<<HB,8); HV1=calloc(1ULL<<HB,1); HK2=calloc(1ULL<<HB,8); HV2=calloc(1ULL<<HB,1);
  if(argc>4){ // check mode: argv[4] = comma list of Q5 points of a closed walk; run phase2 on it only
    int m=0; char*s=argv[4]; qw[0]=atoi(s); while((s=strchr(s,','))){ s++; qw[++m]=atoi(s); }
    for(int j=0;j<m;j++){ int dz=qw[j]^qw[j+1]; qg[j]=__builtin_ctz(dz); }
    phase2(m); printf("check: m=%d n2=%lld found=%lld\n",m,n2,found); return 0; }
  { char*pp=getenv("PREFIX"); if(pp){ for(char*c=pp;*c;c++) PRE[NPRE++]=*c-'0'; } }
  memset(leaves1,0,sizeof(leaves1)); qw[0]=0;
  dfs1(0,0,1u<<0,1u<<0,-1);
  printf("DONE LT=%d split %d/%d n1=%lld n2=%lld found=%lld feas1=%lld feas2=%lld mismatches=%lld\n",LT,SPLIT,NSPLIT,n1,n2,found,nfeas1,nfeas2,nmis);
  for(int m=16;m<=LT;m+=2) printf(" m=%d closed-cover walks=%lld sigma-feasible=%lld\n",m,leaves1[m],leaves1[m+32]);
  return 0;
}
