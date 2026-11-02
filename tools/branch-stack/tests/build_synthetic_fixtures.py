"""Build genuine owned synthetic Git objects. Run before immutable qualification."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from adapter_support import ProcessCapture, git_environment, record
os.umask(0o077)
root=Path(os.environ["ADAPTER_FIXTURE_HOME"])
root.mkdir(mode=0o700)
cap=ProcessCapture(root/"producer-captures",max_launches=200)
env=git_environment(root)
repo=root/"source.git"; template=root/"template"; template.mkdir()
objects=[]
def git(*args,data=None):
    r=cap.run(["/usr/bin/git","--git-dir="+str(repo),*args],env=env,input_bytes=data,cwd=root)
    if r["exit_code"]!=0: raise RuntimeError("fixture-native-failure")
    return r["stdout"].decode().strip()
git("init","--bare","--template="+str(template),str(repo))
def blob(raw):
    oid=git("hash-object","-w","--stdin",data=raw)
    if oid not in objects: objects.append(oid)
    return oid
def tree(files):
    # All ordinary synthetic files at root for simple, independently known trees.
    raw="".join("100644 blob "+blob(body)+"\t"+p+"\n" for p,body in sorted(files.items())).encode()
    oid=git("mktree",data=raw)
    if oid not in objects: objects.append(oid)
    return oid
def commit(files,parents):
    t=tree(files)
    data=("tree "+t+"\n"+"".join("parent "+p+"\n" for p in parents)+
          "author Fixture <fixture@invalid> 0 +0000\ncommitter Fixture <fixture@invalid> 0 +0000\n\nSynthetic fixture only.\n").encode()
    h=git("hash-object","-t","commit","-w","--stdin",data=data)
    objects.append(h)
    return {"head":h,"tree":t,"parents":parents,"content":h,"resolution":"synthetic-0"}
base={"shared.py":b"base\n","ordered.py":b"red\ngreen\nblue\n",
      "nway.py":b"a\nb\nc\na\nb\nc\na\nb\nc\n"}
main=commit(base,[])
A=commit(dict(base,**{"foundation.py":b"A\n"}),[main["head"]])
B=commit(dict(base,**{"foundation.py":b"A\n","b.py":b"B\n"}),[A["head"]])
C=commit(dict(base,**{"foundation.py":b"A\n","c.py":b"C\n"}),[A["head"]])
X=commit(dict(base,**{"shared.py":b"X\n"}),[main["head"]])
Y=commit(dict(base,**{"shared.py":b"Y\n"}),[main["head"]])
# Individually clean against Main; folding O1 then O2 conflicts on same line.
O1=commit(dict(base,**{"ordered.py":b"RED\ngreen\nblue\n"}),[main["head"]])
O2=commit(dict(base,**{"ordered.py":b"RUBY\ngreen\nblue\n"}),[main["head"]])
P=commit(dict(base,**{"nway.py":b'a\nX\nc\na\nb\nc\na\nb\nc\n'}),[main["head"]])
Q=commit(dict(base,**{"nway.py":b'a\nb\nc\na\nc\nc\nY\na\nb\nc\n'}),[main["head"]])
S=commit(dict(base,**{"nway.py":b'X\na\nb\nc\na\nb\nc\na\nb\nc\n'}),[main["head"]])
# Driver config belongs only to owned countercontrol fixture, never imported by probe.
evil_base=dict(base,**{".gitattributes":b"shared.py merge=evil\n"})
E0=commit(evil_base,[main["head"]])
E1=commit(dict(evil_base,**{"shared.py":b"evil-left\n"}),[E0["head"]])
E2=commit(dict(evil_base,**{"shared.py":b"evil-right\n"}),[E0["head"]])
marker=Path(os.environ["ADAPTER_COUNTER_MARKER"])
git("config","merge.evil.driver","/usr/bin/touch "+str(marker))
# A real source ref and index sentinel prove no source ref/index writes.
git("update-ref","refs/heads/fixture",main["head"])
(repo/"index").write_bytes(b"synthetic-index-sentinel")
versions=dict(Main=main,A=A,B=B,C=C,X=X,Y=Y,O1=O1,O2=O2,E0=E0,E1=E1,E2=E2,P=P,Q=Q,S=S)
records=[{"oid":oid,"path":str(repo/"objects"/oid[:2]/oid[2:]),
          "bytes":(repo/"objects"/oid[:2]/oid[2:]).stat().st_size,
          "admitted":True,"role":"ADMITTED_COMPLETE_GIT_OBJECT","policy_ref":"fixture/generated-positive"}
         for oid in dict.fromkeys(objects)]
record(root/"fixture.json",{"schema":"owned-real-git-fixture/v1","versions":versions,"records":records,
 "repo":str(repo),"marker":str(marker),
 "scope":{"complete":True,"objects_admitted":True,"backing_kind":"owned-synthetic",
          "admission_ref":"fixture/closed-object-set",
          "paths":[{"path":p,"body_admitted":True,"policy_ref":"fixture/newordinary",
                    "role":"SYNTHETIC_FIXTURE"} for p in
                   [".gitattributes","shared.py","ordered.py","foundation.py","b.py","c.py","nway.py"]]}})
record(root/"fixture-ends.json",cap.ends)
print(json.dumps({"objects":len(records),"launches":len(cap.ends),"native_exits":[e["exit_code"] for e in cap.ends]}))

