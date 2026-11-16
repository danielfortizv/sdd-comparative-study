#!/usr/bin/env python3
"""Audit an E2 SHA-256 manifest without modifying its source tree."""
import argparse, csv, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); root=Path(a.source).resolve(strict=True); mf=Path(a.manifest).resolve(strict=True); out=Path(a.out)
    raw=mf.read_bytes(); text=raw.decode('utf-8-sig')
    dialect=csv.Sniffer().sniff(text[:4096], delimiters=',;\t')
    records=list(csv.DictReader(text.splitlines(), dialect=dialect))
    required={'Ruta','SHA256','Bytes'}
    if not records or not required.issubset(records[0]): raise SystemExit('Unsupported manifest schema')
    seen=set(); rows=[]; duplicates=0
    for i,r in enumerate(records,2):
        rel=(r.get('Ruta') or '').replace('\\','/')
        pp=PurePosixPath(rel); key=pp.as_posix().casefold(); expected=(r.get('SHA256') or '').strip().upper()
        status='MATCH'; actual=''; size=''; detail=''
        try:
            if key in seen: duplicates+=1; status='UNSAFE'; detail='duplicate normalized path'
            seen.add(key)
            if pp.is_absolute() or any(x in ('..','') for x in pp.parts): status='UNSAFE'; detail='absolute or traversal path'
            target=root.joinpath(*pp.parts)
            resolved=target.resolve(strict=False)
            if root not in resolved.parents: status='UNSAFE'; detail='resolved path escapes source'
            elif target.is_symlink(): status='UNSAFE'; detail='symlink entry is not allowed'
            elif not target.is_file(): status='MISSING'; detail='file absent'
            else:
                data=target.read_bytes(); actual=hashlib.sha256(data).hexdigest().upper(); size=len(data)
                if status=='MATCH' and actual!=expected: status='MISMATCH'; detail='sha256 differs'
        except Exception as e: status='ERROR'; detail=f'{type(e).__name__}: {e}'
        rows.append({'record':i,'path':rel,'expected_sha256':expected,'actual_sha256':actual,'expected_bytes':r.get('Bytes',''),'actual_bytes':size,'status':status,'detail':detail})
    out.mkdir(parents=True,exist_ok=True)
    cp=out/'E3_SPECKIT_E2_MANIFEST_AUDIT.csv'; jp=out/'E3_SPECKIT_E2_MANIFEST_AUDIT_SUMMARY.json'
    with cp.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['record','path','expected_sha256','actual_sha256','expected_bytes','actual_bytes','status','detail']); w.writeheader(); w.writerows(rows)
    counts={s:sum(x['status']==s for x in rows) for s in ('MATCH','MISSING','MISMATCH','UNSAFE','ERROR')}
    specific=next((x for x in rows if x['path']=='.gemini/commands/speckit.analyze.toml'),None)
    summary={'expected_manifest_entries':len(records),'processed_entries':len(rows),**{k.lower()+'_count':v for k,v in counts.items()},'duplicate_path_count':duplicates,'audit_completion_status':'PASS' if len(records)==74 and counts['MATCH']==74 and duplicates==0 else 'FAIL','timestamp_utc':datetime.now(timezone.utc).isoformat(),'source_path':str(root),'manifest_path':str(mf),'specific_analyze_command':specific,'audit_csv':str(cp)}
    jp.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2)); return 0 if summary['audit_completion_status']=='PASS' else 2
if __name__=='__main__': sys.exit(main())
