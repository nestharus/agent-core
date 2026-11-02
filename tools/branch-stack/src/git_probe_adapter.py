"""Real stock-Git text probes in a fresh private bare object database.

The only imported objects are individually named, positively admitted loose-object
backings. No alternates, repository config, source refs/index/worktree or network.
Ordered folds create disposable virtual commit OBJECTS (no refs) in this database.
They carry no signatures/approval and are never published or reused as feature tips.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import zlib
from adapter_support import AdapterError, need, ProcessCapture, git_environment, record

SAFE_PATH = re.compile(r"^[A-Za-z0-9_./ -]{1,1024}$")
OID = re.compile(r"^[0-9a-f]{40}$")

def ordinary_path(path):
    return (isinstance(path,str) and SAFE_PATH.fullmatch(path) and not path.startswith("/")
            and all(p not in ("",".","..") for p in path.split("/")))

class NativeFailure(AdapterError):
    pass

def owned_bytes(root):
    # root is exclusively this fresh owned probe directory, never a discovery root.
    size=0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for f in files:
            p=Path(directory)/f
            need(not p.is_symlink(),"owned-output-symlink")
            size+=p.stat().st_size
    return size

class GitProbe:
    def __init__(self, core, directory, *, timeout=10, max_bytes=64*1024**2,
                 min_free=40*1024**3, diff_algorithm="histogram"):
        self.core=core; self.root=Path(directory)
        need(self.root.is_absolute() and not self.root.exists(),"fresh-owned-probe-required")
        need(0 < max_bytes <= 128*1024**2, "object-disk-budget")
        self.root.mkdir(mode=0o700)
        need(diff_algorithm == "histogram","qualified-diff-algorithm")
        self.diff_algorithm=diff_algorithm
        self.max_bytes=max_bytes; self.min_free=min_free
        self.capture=ProcessCapture(self.root/"processes", timeout=timeout)
        self.repo=self.root/"probe.git"
        self.env=git_environment(self.root)
        self.ready=False
        self.imported=[]
        self.budget()

    def budget(self):
        size=owned_bytes(self.root)
        free=os.statvfs(self.root).f_bavail*os.statvfs(self.root).f_frsize
        need(size <= self.max_bytes,"owned-probe-disk-budget")
        need(free >= self.min_free,"minimum-free-space-frontier")
        return {"owned_logical_bytes":size,"free_bytes":free}

    def git(self, *args, data=None):
        self.budget()
        argv=["/usr/bin/git","--git-dir="+str(self.repo),
              "-c","core.hooksPath=/dev/null","-c","core.fsmonitor=false",
              "-c","core.attributesFile=/dev/null","-c","protocol.allow=never",
              "-c","merge.renormalize=false","-c","gc.auto=0",
              "-c","maintenance.auto=false",*args]
        r=self.capture.run(argv,env=self.env,input_bytes=data,cwd=self.root)
        self.budget()
        return r

    def successful(self,r):
        if r["exit_code"]!=0 or r["timed_out"] or r["launch_error"]:
            raise NativeFailure("native-process-failure")
        return r["stdout"]

    def initialize(self):
        version=self.capture.run(["/usr/bin/git","--version"],env=self.env)
        help_=self.capture.run(["/usr/bin/git","merge-tree","-h"],env=self.env)
        self.successful(version)
        need(help_["exit_code"]==129 and all(x in help_["stdout"]+help_["stderr"]
             for x in (b"--write-tree",b"--name-only",b"merge-base",b"-z")), "stock-git-capability-UNKNOWN")
        empty=self.root/"empty-template"; empty.mkdir(mode=0o700)
        self.successful(self.git("init","--bare","--template="+str(empty),str(self.repo)))
        # Highest attribute precedence overrides all tree-provided merge/filter choices.
        (self.repo/"info").mkdir(mode=0o700, exist_ok=True)
        (self.repo/"info"/"attributes").write_text("* merge=text -filter -diff -text\n")
        self.ready=True

    def preflight(self, snapshot, order, kind, main_version, scope):
        g=self.core.Graph(snapshot)
        need(kind in ("pair","ordered"),"probe-kind")
        need(isinstance(order,list) and order and len(order)<=100
             and len(order)==len(set(order)) and set(order)<=g.units.keys(),"explicit-once-order")
        need(kind!="pair" or len(order)==2,"pair-arity")
        self.core.version(main_version)
        # Core accepts future 64-hex Git metadata; this backend only consumes SHA1.
        # Gate only actual Git identities, never version/content/evidence digests.
        git_oids=[snapshot["main"]]
        for v in [main_version]+[g.units[u]["version"] for u in order]:
            git_oids.extend([v["head"],v["tree"],*v["parents"]])
        git_oids.extend(g.units[u]["physical_base"]["head"] for u in order)
        need(all(isinstance(x,str) and OID.fullmatch(x) for x in git_oids),
             "unsupported-Git-object-format-before-init-or-getter")
        need(main_version["head"]==snapshot["main"],"expected-Main-mismatch")
        if kind=="ordered":
            need(any(x["order"]==order for x in g.groups),"expected-selected-order-mismatch")
        need(all(g.units[u]["admitted"] for u in order),"counterpart-unadmitted-before-getter")
        need(scope.get("complete") is True and scope.get("objects_admitted") is True
             and scope.get("backing_kind") in ("owned-synthetic","positive-readonly-transport")
             and scope.get("admission_ref"),"source-scope-UNKNOWN-before-getter")
        paths=scope.get("paths")
        need(isinstance(paths,list) and len(paths)<=10000,"path-scope-UNKNOWN-before-getter")
        names=set()
        for p in paths:
            need(ordinary_path(p["path"]) and p["path"] not in names
                 and p.get("body_admitted") is True and p.get("policy_ref")
                 and p.get("role") in ("ORDINARY_PROGRAM","SYNTHETIC_FIXTURE"),
                 "path-body-capability-UNKNOWN-before-getter")
            names.add(p["path"])
        return g,names

    def import_objects(self, records):
        need(isinstance(records,list) and len(records)<=10000,"positive-object-list-budget")
        total=0; seen=set()
        # Inspect all capabilities before any backing getter/read.
        for r in records:
            need(OID.fullmatch(r["oid"]) and r["oid"] not in seen and
                 r.get("admitted") is True and r.get("policy_ref") and
                 r.get("role")=="ADMITTED_COMPLETE_GIT_OBJECT" and
                 isinstance(r["path"],str) and Path(r["path"]).is_absolute() and
                 type(r["bytes"]) is int and 0 < r["bytes"]<=8*1024**2,
                 "object-capability-UNKNOWN")
            seen.add(r["oid"]); total+=r["bytes"]
        need(total<=self.max_bytes//2,"object-import-byte-budget")
        for r in records:
            path=Path(r["path"])
            need(path.resolve()==path and not path.is_symlink(),"literal-positive-backing-only")
            with path.open("rb") as f: raw=f.read(r["bytes"]+1)
            need(len(raw)==r["bytes"],"backing-size-CAS")
            dec=zlib.decompressobj()
            data=dec.decompress(raw,8*1024**2+1)
            need(len(data)<=8*1024**2 and dec.eof and not dec.unused_data
                 and hashlib.sha1(data).hexdigest()==r["oid"],"object-byte-CAS")
            header,body=data.split(b"\0",1)
            typ,length=header.split(b" ")
            need(typ in (b"blob",b"tree",b"commit") and int(length)==len(body),"object-format")
            dest=self.repo/"objects"/r["oid"][:2]/r["oid"][2:]
            dest.parent.mkdir(mode=0o700,exist_ok=True)
            # Same object is canonical once; no overwrites.
            fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,"wb") as f: f.write(raw)
            self.imported.append(r["oid"])
            self.budget()

    def verify_version(self, expected, names):
        head=expected["head"]
        raw=self.successful(self.git("show","-s","--no-show-signature","--format=%H%n%T%n%P",head))
        lines=raw.decode("ascii").splitlines()
        need(len(lines)==3 and lines==[head,expected["tree"]," ".join(expected["parents"])],
             "expected-head-tree-orderedparents-CAS")
        raw=self.successful(self.git("ls-tree","-rz","--full-tree",head))
        for entry in raw.split(b"\0"):
            if not entry: continue
            meta,path=entry.split(b"\t",1)
            mode,typ,oid=meta.split()
            need(typ==b"blob" and mode in (b"100644",b"100755") and
                 path.decode("utf8") in names,"actual-tree-path-or-mode-unadmitted")
        # No missing paths are interpreted as all-counterparts admitted: scope.complete
        # explicitly asserts the closed union, and every traversed object is imported.

    def virtual_commit(self, tree, parents):
        data=("tree "+tree+"\n"+"".join("parent "+p+"\n" for p in parents)+
              "author Probe <probe@invalid> 0 +0000\ncommitter Probe <probe@invalid> 0 +0000\n\n"
              "Disposable ordered probe. No feature/ref/public identity.\n").encode()
        raw=self.successful(self.git("hash-object","-t","commit","-w","--stdin",data=data))
        oid=raw.decode().strip()
        need(OID.fullmatch(oid),"native-virtual-object-format")
        return oid

    def probe(self, snapshot, order, *, kind, main_version, scope, source_getter):
        """source_getter is called only after all scope/counterpart gates.

        FAILURE is kept distinct in envelope; core receives UNKNOWN, never CONFLICT
        from a non-1 native exit. CLEAN text always semantic=False.
        """
        p={"kind":kind,"units":list(order),
           "versions":{},"base":snapshot["main"],"status":"UNKNOWN","paths":[],
           "reason":"source-scope-UNKNOWN","evidence_ref":"probe/owned","admitted":False,"semantic":False}
        envelope={"schema":"native-git-probe/v1","status":"UNKNOWN","semantic_frontier":"UNKNOWN",
                  "diff_algorithm":self.diff_algorithm,"trace":[],"probe":p,"mutations":{"source_refs":False,"source_index":False,
                  "source_worktree":False,"feature_commits":False,"private_virtual_objects":True}}
        try:
            g,names=self.preflight(snapshot,order,kind,main_version,scope)
            p["versions"]={u:g.keys[u] for u in order}
            p["evidence_ref"]="native-probe/"+self.core.digest({"directory":str(self.root),
                "main":snapshot["main"],"versions":p["versions"],"order":order,
                "kind":kind,"diff_algorithm":self.diff_algorithm,"admission_ref":scope["admission_ref"]})
            if not self.ready: self.initialize()
            self.import_objects(source_getter())
            for v in [main_version]+[g.units[u]["version"] for u in order]:
                self.verify_version(v,names)
            p["admitted"]=True
            current=snapshot["main"]
            # Pair uses branch pair directly, not an ordered Main fold.
            steps=[(order[1],g.units[order[0]]["version"]["head"])] if kind=="pair" else [(u,None) for u in order]
            for u,left in steps:
                head=g.units[u]["version"]["head"]
                left=left or current
                r=self.git("merge-tree","--write-tree","--name-only","--no-messages","-z","-Xdiff-algorithm="+self.diff_algorithm,left,head)
                trace={"unit":u,"native_exit":r["exit_code"],"timed_out":r["timed_out"],
                       "capture":r["capture"]}
                envelope["trace"].append(trace)
                if r["timed_out"] or r["launch_error"] or r["exit_code"] not in (0,1):
                    envelope["status"]="FAILURE";p["reason"]="native-process-failure";break
                fields=r["stdout"].split(b"\0")
                tree=fields[0].decode("ascii").strip()
                need(OID.fullmatch(tree),"native-output-tree-format")
                if r["exit_code"]==1:
                    locations=[]
                    for raw in fields[1:]:
                        if not raw: continue
                        path=raw.decode("utf8")
                        need(path in names and ordinary_path(path),"conflict-location-unadmitted")
                        locations.append({"path":path,"ordinary_safe":True})
                    need(locations and len(locations)<=128,"conflict-path-output-UNKNOWN")
                    p.update(status="CONFLICT",paths=locations,reason="native-text-conflict")
                    envelope["status"]="CONFLICT";break
                need(not any(fields[1:]),"unexpected-clean-native-output")
                trace["result_tree"]=tree
                current=self.virtual_commit(tree,[left,head]) if left!=head else left
            else:
                p.update(status="CLEAN",reason="native-text-clean-semantic-UNKNOWN")
                envelope.update(status="CLEAN",result_tip=current)
        except (AdapterError,OSError,ValueError,KeyError,UnicodeError) as exc:
            envelope["status"]="FAILURE" if isinstance(exc,NativeFailure) or p["admitted"] else "UNKNOWN"
            p.update(status="UNKNOWN",paths=[],reason=(str(exc) if isinstance(exc,AdapterError)
                                                     else "invalid-or-unavailable-native-input"))
        envelope["reason"]=p["reason"]
        if not p["versions"]:
            # Strict core cannot represent missing unit/version bindings. Keep envelope
            # only; caller must not append a malformed or invented probe.
            envelope["probe"]=None
        envelope["native_ends"]=list(self.capture.ends)
        envelope["resource_sample"]=self.budget()
        record(self.root/"probe-result.json",envelope)
        return envelope



def readonly_metadata(core, *, git_dir, main_ref, selections, capture_dir, pinned_heads=None):
    """Read explicit refs and immutable commits from a normal RO Git database.

    Packed/loose objects are Git's responsibility. No product execution, network,
    merge/filter driver, hook, source worktree write or logical-edge inference.
    Ref reads bracket metadata reads; a changed ref fails instead of mixing pins.
    selections is a bounded list of {number, ref, physical_base_ref}.
    """
    from datetime import datetime, timezone
    need(Path(git_dir).is_absolute() and type(selections) is list and 0<len(selections)<=100,
         "explicit-bounded-Git-metadata-selection")
    refs=[main_ref]
    for row in selections:
        need(type(row["number"]) is int and row["number"]>0,"typed-selected-PR")
        refs.extend((row["ref"],row["physical_base_ref"]))
    refs=list(dict.fromkeys(refs))
    need(all(isinstance(ref,str) and ref.startswith("refs/heads/") and
             re.fullmatch(r"refs/heads/[A-Za-z0-9_./-]+",ref) and ".." not in ref for ref in refs),
         "literal-selected-local-refs")
    root=Path(capture_dir); root.mkdir(mode=0o700)
    cap=ProcessCapture(root/"processes",timeout=10,max_launches=400)
    env=git_environment(root)
    prefix=["/usr/bin/git","--no-optional-locks","--git-dir="+str(git_dir),
        "-c","core.hooksPath=/dev/null","-c","core.fsmonitor=false",
        "-c","core.attributesFile=/dev/null","-c","protocol.allow=never",
        "-c","gc.auto=0","-c","maintenance.auto=false"]
    def read(*args):
        result=cap.run(prefix+list(args),env=env)
        need(result["exit_code"]==0 and not result["timed_out"] and not result["launch_error"],
             "readonly-Git-metadata-unavailable")
        return result["stdout"].decode("ascii").strip()
    started=datetime.now(timezone.utc).isoformat()
    if pinned_heads is None:
        heads={ref:core.oid(read("rev-parse","--verify",ref+"^{commit}")) for ref in refs}
    else:
        need(type(pinned_heads) is dict and set(pinned_heads)==set(refs),"exact-upstream-ref-pin-set")
        heads={ref:core.oid(pinned_heads[ref]) for ref in refs}
    versions={}
    for head in dict.fromkeys(heads.values()):
        raw=read("show","--no-patch","--no-show-signature","--format=%H%n%T%n%P",head).splitlines()
        need(len(raw) in (2,3) and raw[0]==head,"readonly-Git-commit-CAS")
        versions[head]={"head":head,"tree":core.oid(raw[1]),
                        "parents":[core.oid(v) for v in (raw[2].split() if len(raw)==3 else [])]}
    if pinned_heads is None:
        need(all(read("rev-parse","--verify",ref+"^{commit}")==head for ref,head in heads.items()),
             "readonly-Git-ref-changed-during-observation")
    result={"schema":"readonly-Git-structure/v1","source_git_dir":str(git_dir),
        "started_at":started,"observed_at":datetime.now(timezone.utc).isoformat(),
        "main":{"ref":main_ref,**versions[heads[main_ref]]},
        "units":[{"number":r["number"],"ref":r["ref"],**versions[heads[r["ref"]]],
                  "physical_base":{"ref":r["physical_base_ref"],"head":heads[r["physical_base_ref"]]}}
                 for r in selections],
        "status":"METADATA_VERIFIED",
        "ref_binding":"BRACKETED_LOCAL_REFS" if pinned_heads is None else "EXPLICIT_UPSTREAM_PINS_LOCAL_REFS_NOT_ASSERTED",
        "logical_dependencies":"UNKNOWN",
        "semantic":"UNKNOWN","source_writes":False,"network":False}
    record(root/"metadata.json",result)
    return result
