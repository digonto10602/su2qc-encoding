// Tester 444: INDEPENDENT brute force of phase 2 (own code, own labels file, exact arithmetic mod 2^61-1, incremental basis).
// stdin: lines "m q0 q1 ... qm" = closed Q5 walks (Q5 point = low4 bits | a<<4).  argv: LT labelfile.
// For each walk enumerate ALL raw lifts to F2^6 (p=1,y1=2,y2=4,y3=8,e=16,a=32; generators 1,2,4,8,16,32,48): start e0 in {0,1}; at every
// position i=0..m any number n>=0 of e-moves with total <= K=LT-m (NO domination assumption: n=0,1,2,3,.. all enumerated; n>=1 visits both e values at that
// position, e flips if n odd); every a-move may carry an e flip (generator 48).  End anywhere in {0,16}.  A lift is feasible iff g (37 labels) is in the span of
// chi_x, x in visited set (exact rank test over GF(2^61-1)).  Prints per-file totals; with -v prints feasible lifts.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint64_t u64; typedef __uint128_t u128;
#define P ((1ULL<<61)-1)
static inline u64 mulm(u64 a,u64 b){ u128 z=(u128)a*b; u64 r=(u64)(z&P)+(u64)(z>>61); if(r>=P) r-=P; return r; }
static inline u64 addm(u64 a,u64 b){ u64 r=a+b; if(r>=P) r-=P; return r; }
static inline u64 subm(u64 a,u64 b){ return a>=b? a-b : a+P-b; }
static u64 powm(u64 a,u64 e){ u64 r=1; while(e){ if(e&1) r=mulm(r,a); a=mulm(a,a); e>>=1;} return r; }
int NL, lab[64]; long long gint[64]; u64 CHI[64][64], GV[64];
typedef struct { int rank; int piv[40]; u64 v[40][64]; } Basis;
static void add_point(Basis *B,int x){ // reduce chi_x against basis, append if independent
  u64 w[64]; memcpy(w,CHI[x],sizeof(u64)*NL);
  for(int k=0;k<B->rank;k++){ u64 f=w[B->piv[k]]; if(f){ for(int i=0;i<NL;i++) w[i]=subm(w[i],mulm(f,B->v[k][i])); } }
  int pv=-1; for(int i=0;i<NL;i++) if(w[i]){pv=i;break;}
  if(pv<0) return; u64 inv=powm(w[pv],P-2); for(int i=0;i<NL;i++) w[i]=mulm(w[i],inv);
  // keep basis reduced w.r.t. new pivot not required (we reduce sequentially in insertion order)
  B->piv[B->rank]=pv; memcpy(B->v[B->rank],w,sizeof(u64)*NL); B->rank++; }
static int in_span_g(const Basis *B){ u64 w[64]; memcpy(w,GV,sizeof(u64)*NL);
  for(int k=0;k<B->rank;k++){ u64 f=w[B->piv[k]]; if(f){ for(int i=0;i<NL;i++) w[i]=subm(w[i],mulm(f,B->v[k][i])); } }
  for(int i=0;i<NL;i++) if(w[i]) return 0; return 1; }
static inline int pt(int v,int e){ return (v&15)|(e<<4)|(((v>>4)&1)<<5); }
int m,q[64],isA[64],K; long long nlift=0,nfeas=0; int verbose=0; int curwalk;
int nchoice[64]; int dseq[64], cseq[64], e0cur;
static void rec(int i,int e,int rem,Basis *Bin,u64 U,int used){
  // arrive at position i with value e: visit (q[i],e)
  Basis B=*Bin; int x=pt(q[i],e); if(!(U>>x&1)){ add_point(&B,x); U|=1ULL<<x; }
  for(int n=0;n<=rem;n++){
    Basis B2=B; u64 U2=U; if(n>=1){ int x1=pt(q[i],e^1); if(!(U2>>x1&1)){ add_point(&B2,x1); U2|=1ULL<<x1; } }
    int e2=e^(n&1); dseq[i]=n;
    if(i==m){ nlift++; if(in_span_g(&B2)){ nfeas++; if(verbose){ printf("FEAS walk#%d e0=%d used=%d n:",curwalk,e0cur,used+n); for(int j=0;j<=m;j++) printf("%d",dseq[j]); printf(" U=%016llx\n",(unsigned long long)U2);} } continue; }
    if(isA[i]){ for(int c=0;c<2;c++){ cseq[i]=c; rec(i+1,e2^c,rem-n,&B2,U2,used+n); } }
    else rec(i+1,e2,rem-n,&B2,U2,used+n);
  }
}
int main(int argc,char**argv){
  int LT=atoi(argv[1]); FILE*f=fopen(argv[2],"r"); if(!f||fscanf(f,"%d",&NL)!=1) return 1; for(int i=0;i<NL;i++){ double g; if(fscanf(f,"%d %lf",&lab[i],&g)!=2) return 1; gint[i]=(long long)(g<0? g-0.5: g+0.5); } fclose(f);
  if(argc>3 && !strcmp(argv[3],"-v")) verbose=1;
  for(int x=0;x<64;x++) for(int i=0;i<NL;i++) CHI[x][i]=(__builtin_popcount(lab[i]&x)&1)? P-1:1;
  for(int i=0;i<NL;i++) GV[i]= gint[i]>=0? (u64)gint[i] : P-(u64)(-gint[i]);
  long long nwalks=0, walks_with_feas=0;
  while(scanf("%d",&m)==1){ for(int j=0;j<=m;j++) scanf("%d",&q[j]); K=LT-m; if(K<0) continue;
    for(int i=0;i<m;i++) isA[i]= ((q[i]^q[i+1])==16); curwalk=nwalks; long long before=nfeas;
    for(int e0=0;e0<2;e0++){ e0cur=e0; Basis B; B.rank=0; rec(0,e0,K,&B,0,0); }
    nwalks++; if(nfeas>before) walks_with_feas++; }
  printf("BF LT=%d walks=%lld raw_lifts=%lld feasible_lifts=%lld walks_with_feasible_lift=%lld\n",LT,nwalks,nlift,nfeas,walks_with_feas); return 0; }
