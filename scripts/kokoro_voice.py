"""Local Kokoro Alex speech worker. JSON stdin; no external API or secrets."""
from pathlib import Path
import json,sys
import numpy as np
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro

def main():
    job=json.load(sys.stdin)
    if len(job['texts'])!=4 or any(not isinstance(t,str) or len(t)>1200 for t in job['texts']):
        raise ValueError('Expected four bounded narration scenes')
    output=Path(job['output']).resolve()
    root=Path('/home/raul/tuhoy/data/tiktok-media').resolve()
    if not output.is_relative_to(root):raise ValueError('Output must be in video cache')
    output.mkdir(parents=True,exist_ok=True)
    models=Path('/home/raul/.local/share/tuhoy-kokoro-preview/models')
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(models/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    class CompatibleSession:
        def __getattr__(self,name):return getattr(session,name)
        def get_inputs(self):return session.get_inputs()
        def run(self,names,inputs):
            # ONNX export expects float speed; adapt the wrapper's int32 input.
            inputs['speed']=np.asarray(inputs['speed'],dtype=np.float32)
            return session.run(names,inputs)
    model=Kokoro.from_session(CompatibleSession(),str(models/'voices-v1.0.bin'))
    for i,text in enumerate(job['texts']):
        audio,rate=model.create(text,voice='em_alex',speed=1.0,lang='es')
        if not np.isfinite(audio).all() or np.abs(audio).max()<0.001:raise ValueError('Invalid or silent narration')
        sf.write(output/f'voice-{i}.wav',audio,rate,subtype='PCM_16')
if __name__=='__main__':main()
