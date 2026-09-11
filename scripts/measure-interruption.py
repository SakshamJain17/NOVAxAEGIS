"""Measure output silence after annotated interruption onset from a loopback WAV.
Usage: python scripts/measure-interruption.py output.wav --onset 4.25
Input: uncompressed 16-bit PCM mono/stereo loopback recording, no microphone mix.
Annotate --onset from a synchronized mic recording, not a UI click timestamp.
"""
import argparse,json,wave,math,struct
p=argparse.ArgumentParser();p.add_argument('wav');p.add_argument('--onset',type=float,required=True);p.add_argument('--threshold',type=float,default=.003);p.add_argument('--quiet-ms',type=int,default=150);a=p.parse_args()
with wave.open(a.wav,'rb') as w:
 if w.getsampwidth()!=2: raise SystemExit('Requires 16-bit PCM WAV.')
 rate=w.getframerate();channels=w.getnchannels();raw=w.readframes(w.getnframes())
samples=struct.unpack('<'+'h'*(len(raw)//2),raw);hop=max(1,rate//100);start=int(a.onset*rate)
if start<0 or start>=len(samples)//channels:raise SystemExit('Onset is outside the recording.')
quiet=0;stop=None
for pos in range(start,len(samples)//channels-hop,hop):
 block=samples[pos*channels:(pos+hop)*channels];rms=math.sqrt(sum((v/32768)**2 for v in block)/len(block))
 quiet=quiet+10 if rms<a.threshold else 0
 if quiet>=a.quiet_ms:stop=(pos+hop)/rate-quiet/1000;break
result={'input':a.wav,'onset_seconds':a.onset,'silence_seconds':stop,'stop_ms':None if stop is None else round(max(0,stop-a.onset)*1000,2),'threshold_rms':a.threshold,'quiet_window_ms':a.quiet_ms,'limitation':'A natural pause can look like interruption. Inspect the audio and transcript; this metric alone does not prove stale-result isolation.'}
print(json.dumps(result,indent=2))
