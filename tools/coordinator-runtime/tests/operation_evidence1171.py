"""Owned Linux x86_64 syscall experiment; no CLI/provider qualification.

Only exact nonsecret operand syscalls and a fixture loopback connect are kept.
The parent observes kernel entry/exit and allowed-read bytes independently of
worker stdout. Kernel/interpreter/ptrace/bwrap are trusted for this experiment.
"""
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import socket
import struct
import sys

ALLOWED = '/material/allowed.txt'
OUTSIDE = '/outside/nonsecret.txt'
libc = ctypes.CDLL(None, use_errno=True)
libc.ptrace.restype = ctypes.c_long
libc.ptrace.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]


def ptrace(request, pid, address=0, data=0):
    ctypes.set_errno(0)
    value = libc.ptrace(request, pid, address, data)
    error = ctypes.get_errno()
    if value == -1 and error:
        raise OSError(error, os.strerror(error))
    return value


def memory(pid, address, size):
    body = bytearray()
    for offset in range(0, size, 8):
        body.extend((ptrace(2, pid, address+offset) & ((1<<64)-1)).to_bytes(8,'little'))
    return bytes(body[:size])


def path_at(pid, address):
    body = bytearray()
    for offset in range(0, 512, 8):
        word = memory(pid,address+offset,8)
        if b'\0' in word:
            return (body+word.split(b'\0')[0]).decode('utf-8',errors='replace')
        body.extend(word)
    return ''


def syscall_entry(pid, raw, port):
    nr, *args = struct.unpack_from('7Q',raw,24)
    if nr in (2,257):
        index = int(nr==257)
        path = path_at(pid,args[index])
        if path in (ALLOWED,OUTSIDE):
            return dict(operation='open',path=path,flags=args[index+1])
    if nr in (0,1,3):
        return dict(operation={0:'read',1:'write',3:'close'}[nr],fd=args[0],buffer=args[1],count=args[2])
    if nr==42 and args[2]==16:
        address=memory(pid,args[1],16)
        if address[:8]==struct.pack('H',socket.AF_INET)+struct.pack('!H',port)+socket.inet_aton('127.0.0.1'):
            return dict(operation='connect',address='owned-loopback-listener',port=port)
    return None


def syscall_exit(pid, entry, result, descriptors, events):
    if entry is None:
        return
    op=entry['operation']
    if op=='open':
        events.append({**entry,'result':result})
        if result>=0:descriptors[(pid,result)]=entry['path']
        return
    if op=='connect':
        events.append({**entry,'result':result})
        return
    path=descriptors.get((pid,entry['fd']))
    if op=='close':
        descriptors.pop((pid,entry['fd']),None)
        return
    if path is None:
        return
    record=dict(operation=op,path=path,result=result)
    if op=='read' and result>0:
        record['read_sha256']=hashlib.sha256(memory(pid,entry['buffer'],result)).hexdigest()
    events.append(record)


def trace(command,port):
    """This dedicated observer has no other children; wait returns real statuses."""
    child=os.fork()
    if child==0:
        null=os.open('/dev/null',os.O_RDWR)
        os.dup2(null,0);os.dup2(null,1);os.dup2(null,2)
        ptrace(0,0)
        os.kill(os.getpid(),signal.SIGSTOP)
        os.execv(command[0],command)
    pid,status=os.waitpid(child,0)
    assert pid==child and os.WIFSTOPPED(status)
    # syscall stops, owned forks/clones/exec, and kill traced children if the
    # observer dies. No attach, process census or foreign identity is used.
    ptrace(0x4200,child,0,1|2|4|8|16|(1<<20))
    ptrace(24,child)
    active={child}; entries={};descriptors={};events=[];ends={}
    while active:
        pid,status=os.waitpid(-1,0)
        assert pid in active,'unexpected child outside dedicated observer'
        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
            ends[pid]=os.waitstatus_to_exitcode(status);active.remove(pid)
            continue
        stop=os.WSTOPSIG(status);event=status>>16
        if stop==signal.SIGTRAP and event in (1,2,3):
            new=ctypes.c_ulonglong()
            ptrace(0x4201,pid,0,ctypes.addressof(new));active.add(new.value)
        if stop==signal.SIGTRAP|0x80:
            info=ctypes.create_string_buffer(128)
            size=ptrace(0x420e,pid,128,ctypes.addressof(info))
            assert size>=24,'kernel syscall information unavailable'
            raw=info.raw
            if raw[0]==1:entries[pid]=syscall_entry(pid,raw,port)
            if raw[0]==2:syscall_exit(pid,entries.pop(pid,None),struct.unpack_from('q',raw,24)[0],descriptors,events)
        forwarded=stop if stop not in (signal.SIGTRAP,signal.SIGSTOP,signal.SIGTRAP|0x80) else 0
        ptrace(24,pid,0,forwarded)
    return dict(events=events,actual_END=ends[child],descendant_ENDs=list(ends.values()),
                observer='ptrace syscall entry/exit; exact nonsecret operands only')


def worker(mode,port):
    with open(ALLOWED,'rb') as source:
        allowed=source.read()
    if mode!='omitted':
        try:
            with open(OUTSIDE,'rb') as source:source.read()
        except OSError:pass
        try:
            with open(ALLOWED,'wb') as target:target.write(b'actual-weak-write1171')
        except OSError:pass
        try:
            with socket.socket() as client:client.connect(('127.0.0.1',port))
        except OSError:pass
    # Deliberately identical reported denial constants, including in omission
    # and weakened modes. The observer must never rely on these assertions.
    print(json.dumps(dict(allowed=allowed.decode(),denied_read=13,denied_write=30,denied_network=13)))


def qualifies(record,expected):
    events=record['events']
    return (record['actual_END']==0 and all(v==0 for v in record['descendant_ENDs'])
        and any(e['operation']=='read' and e['path']==ALLOWED and e.get('read_sha256')==expected for e in events)
        and any(e['operation']=='open' and e['path']==OUTSIDE and e['result']==-errno.ENOENT for e in events)
        and any(e['operation']=='open' and e['path']==ALLOWED and e['flags']&3 and e['result']==-errno.EROFS for e in events)
        and any(e['operation']=='connect' and e['result']==-errno.ECONNREFUSED for e in events))


def observe(mode,area):
    if platform.machine()!='x86_64':raise RuntimeError('explicit x86_64 syscall ABI required')
    area=Path(area)
    expected=hashlib.sha256((area/'allowed.txt').read_bytes()).hexdigest()
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(4)
    port=server.getsockname()[1]
    command=['/usr/bin/bwrap','--die-with-parent','--new-session',
        '--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64',
        '--ro-bind','/bin','/bin','--proc','/proc','--dev','/dev','--tmpfs','/tmp',
        '--dir','/material','--dir','/outside',
        '--ro-bind',str(Path(__file__)),'/probe.py',
        '--ro-bind' if mode!='weakened' else '--bind',str(area/'allowed.txt'),ALLOWED]
    if mode=='weakened':command+=['--ro-bind',str(area/'outside.txt'),OUTSIDE]
    else:command+=['--unshare-net']
    command+=['--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp',
              '/usr/bin/python3','-I','-B','/probe.py','worker',mode,str(port)]
    try:record=trace(command,port)
    finally:server.close()
    record.update(mode=mode,qualified=qualifies(record,expected),expected_read_sha256=expected,
                  resulting_allowed_sha256=hashlib.sha256((area/'allowed.txt').read_bytes()).hexdigest(),
                  domain='nested owned bwrap fixture; not codex/provider/native/service')
    print(json.dumps(record))


if __name__=='__main__':
    if sys.argv[1]=='worker':worker(sys.argv[2],int(sys.argv[3]))
    elif sys.argv[1]=='observe':observe(sys.argv[2],sys.argv[3])
    else:raise ValueError('explicit worker or observer required')
