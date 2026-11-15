import json, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
R="/home/claude/lorenaguedes/ccf-framework/"
OUT=R+"docs/tcc/fig/"
AZ,LA,INK,SUB,GRID="#2a78d6","#eb6834","#0b0b0b","#52514e","#e3e2de"
plt.rcParams.update({"font.size":10,"axes.edgecolor":GRID,"axes.labelcolor":SUB,"xtick.color":SUB,"ytick.color":SUB,
    "axes.spines.top":False,"axes.spines.right":False,"figure.facecolor":"#fcfcfb","axes.facecolor":"#fcfcfb"})
vir=FuncFormatter(lambda v,_:f"{v:.2f}".replace(".",","))
def carrega(n): return json.load(open(R+f"modulo_integracao/logs/{n}"))["resultado"]
caso,ctrl=carrega("cenario_c4_execucao.json"),carrega("cenario_c4_controle.json")
def est(res,mod,e): return next(x for x in res["evidencias"] if x["modalidade"]==mod)["estagios"][e]
lim=json.load(open(R+"modulo_ia/models/modelo_e4_embeddings.json"))["limiar_f1max"]
dados=[("E1 – similaridade PDQ\ncom a base simulada",est(caso,"imagem","E1")["score_similaridade"],est(ctrl,"imagem","E1")["score_similaridade"],None),
       ("E4 – escore de\naliciamento",est(caso,"texto","E4")["score_grooming"],est(ctrl,"texto","E4")["score_grooming"],lim),
       ("E5 – fração de registros\nanômalos",est(caso,"logs","E5")["n_anomalos"]/est(caso,"logs","E5")["n_registros"],
        est(ctrl,"logs","E5")["n_anomalos"]/est(ctrl,"logs","E5")["n_registros"],None)]
fig,ax=plt.subplots(1,3,figsize=(9,3.4),sharey=True)
for a,(t,c,k,l) in zip(ax,dados):
    b=a.bar([0,1],[c,k],width=0.55,color=[AZ,LA],edgecolor="#fcfcfb",linewidth=2)
    b[0].set_hatch("//");b[1].set_hatch("\\\\")
    for r,v in zip(b,[c,k]): a.text(r.get_x()+r.get_width()/2,v+0.02,f"{v:.3f}".replace(".",","),ha="center",color=INK,fontsize=9)
    if l: a.axhline(l,color=SUB,ls="--",lw=1); a.text(1.45,l+0.02,f"limiar {l:.2f}".replace(".",","),ha="right",color=SUB,fontsize=8)
    a.set_xticks([0,1]);a.set_xticklabels(["Caso","Controle"]);a.set_title(t,fontsize=9.5,color=INK)
    a.set_ylim(0,1.08);a.yaxis.set_major_formatter(vir);a.grid(axis="y",color=GRID,lw=0.8);a.set_axisbelow(True)
fig.tight_layout();fig.savefig(OUT+"fig21_c4_caso_controle.png",dpi=200);plt.close(fig)

e5=pd.DataFrame(json.load(open(R+"modulo_ia/experimentos/resultados_e5.json")))
fig,ax=plt.subplots(1,2,figsize=(9,3.4))
for a,(m,t,alvo,rot) in zip(ax,[("f1","F1-score",0.79,"alvo F1 ≥ 0,79"),("fpr","Taxa de falsos positivos",0.10,"alvo FP < 10%")]):
    for cont,cor,mk,nome in [("0.1",AZ,"o","contaminação 0,1 (usada nos cenários)"),("auto",LA,"s","contaminação automática")]:
        g=e5[e5.contamination==cont].groupby("severidade")[m].agg(["mean","std"]).sort_index()
        a.errorbar(g.index,g["mean"],yerr=g["std"],color=cor,marker=mk,ms=6,lw=2,capsize=3,label=nome,markeredgecolor="#fcfcfb")
    a.axhline(alvo,color=SUB,ls="--",lw=1);a.text(1.0,alvo+(0.015 if m=="f1" else 0.012),rot,ha="right",color=SUB,fontsize=8)
    a.set_xlabel("Severidade da anomalia (1,0 = perfil do módulo)");a.set_title(t,fontsize=9.5,color=INK)
    a.yaxis.set_major_formatter(vir);a.xaxis.set_major_formatter(vir);a.grid(axis="y",color=GRID,lw=0.8)
ax[0].legend(frameon=False,fontsize=8,loc="lower right")
fig.tight_layout();fig.savefig(OUT+"fig20_e5_severidade.png",dpi=200);plt.close(fig)
print(dados)

# Figura 19 - E1 (PDQ): revocacao por transformacao
e1=json.load(open(R+"modulo_ia/experimentos/resultados_e1.json"))
leves=e1["transformacoes_leves"]["por_transformacao_revocacao"]
nomes={"jpeg_q90":"JPEG q90","jpeg_q70":"JPEG q70","jpeg_q50":"JPEG q50","reduz_75":"Redução 75%","reduz_50":"Redução 50%",
       "recorte_5":"Recorte 5%","recorte_10":"Recorte 10%","brilho_+15":"Brilho +15%","brilho_-15":"Brilho −15%",
       "desfoque_r1":"Desfoque","marca_dagua":"Marca-d'água"}
import numpy as np
ks=list(nomes); x=np.arange(len(ks)); w=0.38
fig,a=plt.subplots(figsize=(9,3.8))
b1=a.bar(x-w/2,[leves[k]["10"] for k in ks],w,color=LA,edgecolor="#fcfcfb",linewidth=2,label="limiar de 10 bits (padrão do módulo)",hatch="\\\\")
b2=a.bar(x+w/2,[leves[k]["31"] for k in ks],w,color=AZ,edgecolor="#fcfcfb",linewidth=2,label="limiar de 31 bits",hatch="//")
a.axhline(0.99,color=SUB,ls="--",lw=1);a.text(len(ks)-0.5,1.01,"alvo de revocação ≥ 0,99",ha="right",color=SUB,fontsize=8)
a.set_xticks(x);a.set_xticklabels([nomes[k] for k in ks],rotation=30,ha="right")
a.set_ylim(0,1.12);a.set_ylabel("Revocação (200 referências por transformação)");a.yaxis.set_major_formatter(vir)
a.grid(axis="y",color=GRID,lw=0.8);a.set_axisbelow(True);a.legend(frameon=False,fontsize=8,loc="lower left")
fig.tight_layout();fig.savefig(OUT+"fig19_e1_pdq_transformacoes.png",dpi=200);plt.close(fig)
