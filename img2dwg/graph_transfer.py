"""Explicit label-aware expansion; source state and prediction semantics are retained."""
import hashlib
import json
from pathlib import Path
from safetensors.torch import load_file


def initialize(model, source, destination):
    source=Path(source)
    old=json.loads((source.parent/'config.json').read_text(encoding='utf-8'))
    old_library=json.loads((source.parent/'library.json').read_text(encoding='utf-8'))
    current=model.state_dict();state=load_file(str(source));copied=[];partial=[];omitted=[]
    for key,value in state.items():
        if key in current and current[key].shape==value.shape:
            current[key]=value;copied.append(key)
        elif key in ('node_queries.weight','component_queries.weight','node_grid','component_grid'):
            count=min(len(value),len(current[key]));current[key][:count]=value[:count]
            partial.append({'key':key,'prefix':count})
        elif key in ('text.weight','text.bias','template.weight','template.bias'):
            labels=old['texts'] if key.startswith('text.') else ['<unknown>']+sorted(old_library)
            new=destination['texts'] if key.startswith('text.') else ['<unknown>']+sorted(destination['library'])
            positions={label:i for i,label in enumerate(new)}
            for i,label in enumerate(labels):
                if label in positions:current[key][positions[label]]=value[i]
            partial.append({'key':key,'mapped_labels':sum(label in positions for label in labels)})
        elif key.startswith('node_digits.') or key.startswith('size_digits.'):
            groups=2 if key.startswith('node_digits.') else 7
            old_digits=value.shape[0]//groups//10;new_digits=current[key].shape[0]//groups//10
            if new_digits<old_digits:raise ValueError('Cannot truncate initializer numeric vocabulary')
            dst=current[key].reshape(groups,new_digits,10,*current[key].shape[1:])
            dst[:,-old_digits:]=value.reshape(groups,old_digits,10,*value.shape[1:])
            if key.endswith('bias'):dst[:,:new_digits-old_digits,0]=8.
            partial.append({'key':key,'old_digits':old_digits,'new_digits':new_digits})
        else:omitted.append(key)
    if omitted:raise ValueError('Unmapped initializer fields: '+str(omitted))
    model.load_state_dict(current,strict=True)
    return {'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'copied':copied,'partial':partial,'omitted':omitted}
