import numpy as np, subprocess, json
FPS=30; T=22.6; N=int(T*FPS)
def load(f):
    raw=subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar','24000','-f','s16le','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.int16).astype(float)/32768
def env(x, start):
    hop=24000//FPS; out=np.zeros(N)
    r=np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop]**2)) for i in range(len(x)//hop)])
    r=np.clip(r/np.percentile(r[r>0.01],90),0,1)
    s=0
    for i,v in enumerate(r):
        s=max(v,s*0.55); j=int(start*FPS)+i
        if j<N: out[j]=s
    nz=np.where(r>0.05)[0]
    return out, start+nz[0]/FPS, start+nz[-1]/FPS
fa,fb=7.75,None
f,f0,f1=env(load('f.mp3'),7.65)
m,m0,m1=env(load('m.mp3'),f1+0.55)
print('F',f0,f1,'M_start',f1+0.55,'M',m0,m1)
json.dump({'m':[round(v,3) for v in m],'f':[round(v,3) for v in f]},open('mouth.json','w'))
json.dump({'f':[f0,f1],'m':[m0,m1],'mdelay':f1+0.55},open('tempos.json','w'))
