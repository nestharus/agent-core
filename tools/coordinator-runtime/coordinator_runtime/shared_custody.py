"""Public shared delivery conservation and qualified residency retirement.

The actual recipient consents, then the actual Work issuer conserves the exact
envelope with an accountable custodian before retiring owned shared output.
Canonical targets, foreign replies and notification uncertainty are excluded.
The durable compact scan frontier survives disposable local metadata. This is
cooperating SQLite publication, not cross-database atomicity or physical shrink.
"""
import json
import math
import os
from pathlib import Path

from .contracts import Refusal,digest,encode,required_text,regular_path
from .capacity import HOLDS,RETENTION
from .frontier import require_aged,delivery
from .resource_scopes import root

SCHEMA="""
CREATE TABLE IF NOT EXISTS coordinator_custody_consents_v1(
 delivery TEXT PRIMARY KEY,basis TEXT NOT NULL,recipient TEXT NOT NULL,receipt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_scan_frontiers_v1(
 runtime TEXT NOT NULL,device INTEGER NOT NULL,inode INTEGER NOT NULL,actor TEXT NOT NULL,
 through INTEGER NOT NULL,count INTEGER NOT NULL,chain TEXT NOT NULL,
 PRIMARY KEY(runtime,device,inode,actor));
"""


def envelope(board,conn,store,key):
    row=conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?',(key,)).fetchone()
    if not row:
        raise Refusal('exact active shared delivery required; archived originals are never reposted')
    row=dict(row)
    grant=dict(conn.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?',(row['grant_id'],)).fetchone() or {})
    info=store.path.stat()
    if (grant.get('runtime'),grant.get('runtime_dev'),grant.get('runtime_ino'),row['actor'],row['owner'])!=(str(store.path),info.st_dev,info.st_ino,store.config['actor'],board.selected['owner']):
        raise Refusal('foreign/shared delivery belongs to its actual original custodian')
    outbox=store.one('SELECT * FROM outboxes WHERE id=?',(key,))
    if not outbox or outbox['payload']!=row['payload'] or outbox['producer']!=row['producer']:
        raise Refusal('exact original local source/outbox must remain until shared conservation')
    def rows(table,column,value):
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
            return []
        return [dict(r) for r in conn.execute(f'SELECT * FROM {table} WHERE {column}=?',(value,))]
    material={'delivery':row,'grant':grant,'outbox':outbox,'frontier':delivery(store,key),
              'software':rows('coordinator_software_deliveries_v1','delivery',key),
              'checks':rows('coordinator_owner_return_checks_v1','delivery',key),
              'corrections':rows('coordinator_owner_corrections_v1','delivery',key),
              'post':rows('posts','seq',row['post']), 'threads':rows('threads','thread_id',row['post']),
              'thread_posts':rows('thread_posts','thread_id',row['post']),
              'subscriptions':rows('subscriptions','thread_id',row['post']),
              'attachments':rows('attachments','post_seq',row['post']),
              'notices':rows('notification_outbox','post_seq',row['post'])}
    material['notice_attempts']=[a for n in material['notices'] for a in rows('notification_attempts','notification_id',n['notification_id'])]
    return {'basis':digest(material),'material':material,
            'meaning':'full canonical envelope and actual frontier, not eligibility or inferred consent'}


def fresh(store,receipt,basis):
    if (receipt.get('basis')!=basis or receipt.get('holds')!={h:[] for h in HOLDS}
            or type(receipt.get('qualified_at')) not in {int,float} or not math.isfinite(receipt['qualified_at'])
            or not 0<=store.clock()-receipt['qualified_at']<=60):
        raise Refusal('current exact source/frontier and actual all-custodian qualification required')
    required_text(receipt.get('evidence'),'actual custody/consumer/retention evidence')


class SharedCustody:
    def conserved_receiving_material(self, store, conn, key):
        """Exact observed conservation evidence; callers still require grants.

        No shared row is reconstructed. The copy must still be in custody until
        the local software consumer retires; release first conserves no usable
        receiving evidence here. Ordinary processing never calls this accessor.
        """
        intent = store.one("SELECT * FROM shared_custody_intents WHERE delivery=? AND state='retired'", (key,))
        if not intent or not intent['receipt']:
            raise Refusal('exact observed shared conservation intent required')
        archive = Path(intent['archive'])
        if not archive.is_relative_to(store.home/'shared-custody'):
            raise Refusal('receiving evidence must remain in exact owned archive custody')
        archive = regular_path(str(root(str(archive), store.config.get('artifact_exclusions', []))))
        try:
            witness = json.loads(archive.read_text())
            observed = json.loads(intent['receipt'])
        except (OSError, ValueError) as exc:
            raise Refusal('conserved receiving evidence unavailable; preserve local custody') from exc
        original = witness.get('original', {})
        material = original.get('material', {})
        if (original.get('basis') != intent['basis'] or digest(material) != intent['basis']
                or observed.get('delivery') != key or observed.get('canonical_archive') != str(archive)
                or observed.get('archive_hash') != digest(witness)
                or type(observed.get('conserved_at')) not in {int, float}
                or not math.isfinite(observed['conserved_at']) or observed['conserved_at'] > store.clock()
                or witness.get('issuer') != store.processing.current()[0]['issuer']):
            raise Refusal('exact original envelope and observed conservation binding required')
        return self._conserved_receiving_frontier(store, conn, key, material)

    def _conserved_receiving_frontier(self, store, conn, key, material):
        row = material.get('delivery', {})
        software, notices = material.get('software', []), material.get('notices', [])
        outbox = store.one('SELECT * FROM outboxes WHERE id=?', (key,))
        if (row.get('id') != key or len(software) != 1 or software[0].get('delivery') != key
                or len(notices) != 1 or notices[0].get('notification_id') != row.get('notice')
                or notices[0].get('delivery_state') != 'acknowledged'
                or row.get('state') != 'settled' or material.get('outbox') != outbox
                or not material.get('frontier', {}).get('event')
                or material['frontier'] != delivery(store, key) or not material['frontier']['complete']):
            raise Refusal('exact conserved delivery/software/transport/whole consumer required')
        info = store.path.stat()
        frontier = conn.execute('SELECT * FROM coordinator_scan_frontiers_v1 WHERE runtime=? AND device=? AND inode=? AND actor=?',
                                (str(store.path), info.st_dev, info.st_ino, store.config['actor'])).fetchone()
        if not frontier or frontier['through'] < row['post']:
            raise Refusal('original shared conservation frontier unobserved')
        if (conn.execute('SELECT 1 FROM coordinator_deliveries_v1 WHERE id=?', (key,)).fetchone()
                or conn.execute('SELECT 1 FROM coordinator_software_deliveries_v1 WHERE delivery=?', (key,)).fetchone()
                or conn.execute('SELECT 1 FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()):
            raise Refusal('conserved receiving evidence requires exact shared retirement absence')
        require_aged(store, key, RETENTION)
        return material

    def shared_custody_basis(self,store,key):
        with self.opened(settlement=True,owner_required=False) as conn:
            return envelope(self,conn,store,key)

    def shared_custody_consent(self,store,key,receipt):
        """Actual recipient closes all consumers/reply obligations, not ACK."""
        with self.opened(settlement=True,owner_required=False) as conn:
            conn.executescript(SCHEMA)
            with self.store.write(conn):
                current=envelope(self,conn,store,key)
                recipient=current['material']['delivery']['recipient']
                software=current['material']['software']
                # An actually completed delegated software consumer can supply
                # its own custody through its real Work issuer. Do not add a
                # native-owner/model call for every processed software item.
                intent=next((s for s in software if s.get('receiver_grant')),None)
                delegated=False
                if intent:
                    receiver=conn.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?',(intent['receiver_grant'],)).fetchone()
                    info=store.path.stat()
                    delegated=bool(receiver and receiver['issued_by']==store.processing.current()[0]['issuer']
                                   and receiver['runtime']==str(store.path) and receiver['runtime_dev']==info.st_dev
                                   and receiver['runtime_ino']==info.st_ino and current['material']['frontier']['complete']
                                   and current['material']['outbox']['state']=='settled')
                actor=self.store.acting_session(store.processing.current()[0]['issuer'] if delegated else recipient)
                fresh(store,receipt,current['basis'])
                if set(receipt)!={'basis','holds','qualified_at','evidence','reply_route_closed','conservation'} or receipt['reply_route_closed'] is not True:
                    raise Refusal('actual recipient must close reply route and conserve every required original')
                required_text(receipt['conservation'],'actual required source/results/history conservation')
                conn.execute('INSERT INTO coordinator_custody_consents_v1 VALUES(?,?,?,?) ON CONFLICT(delivery) DO UPDATE SET basis=excluded.basis,recipient=excluded.recipient,receipt=excluded.receipt',
                             (key,current['basis'],recipient,encode({'actual_custodian':actor,'delegated_software':delegated,
                                                                    'native_owner_full_read':False,**receipt})))
        return {'delivery':key,'recipient':recipient,'actual_custodian':actor,'delegated_software':delegated,
                'receipt':receipt,'processing_completion_inferred':False}

    def retire_shared_custody(self,store,key,receipt):
        actor=self.store.acting_session(store.config['software_delegation']['grantor'])
        cap,_=store.processing.current()
        if actor!=cap['issuer']:
            raise Refusal('genuine current Work issuer required')
        fields={'basis','holds','qualified_at','evidence','custodian','archive','archive_budget_bytes','archive_existing_bytes','conservation'}
        if not isinstance(receipt,dict) or set(receipt)!=fields:
            raise Refusal('exact envelope/custodian/archive/current cumulative budget and conservation required')
        for f in ('custodian','archive','conservation'):
            required_text(receipt[f],'actual shared custody '+f)
        # Archive is explicit owned custody, never a profile, canonical target,
        # foreign store or copied source. Its custodian accounts cumulative bytes.
        archive=root(receipt['archive'],store.config.get('artifact_exclusions',[]))
        if not archive.is_relative_to(store.home/'shared-custody') or archive==store.home/'shared-custody':
            raise Refusal('archive must be an exact owned shared-custody file')
        with store.tx():
            old=store.one('SELECT * FROM shared_custody_intents WHERE delivery=?',(key,))
            if old and (old['archive']!=str(archive) or old['basis']!=receipt['basis'] or old['state']=='retired'):
                raise Refusal('existing shared conservation intent owns this source; reconcile it explicitly')
            store.db.execute("INSERT OR IGNORE INTO shared_custody_intents VALUES(?,?,?,'prepared',NULL)",(key,str(archive),receipt['basis']))
        with self.opened(settlement=True,owner_required=False) as conn:
            conn.executescript(SCHEMA)
            with self.store.write(conn):
                current=envelope(self,conn,store,key); material=current['material']; row=material['delivery']; outbox=material['outbox']
                fresh(store,receipt,current['basis'])
                consent=conn.execute('SELECT * FROM coordinator_custody_consents_v1 WHERE delivery=?',(key,)).fetchone()
                if not consent or consent['basis']!=current['basis'] or consent['recipient']!=row['recipient']:
                    raise Refusal('actual recipient exact current conservation/closed reply route consent required')
                require_aged(store,key,RETENTION)
                current_status=self._delivery_record(conn,row)
                if (row['state']!='settled' or row['processed_at'] is None or store.clock()<row['processed_at']+RETENTION
                        or outbox['state']!='settled' or outbox['processed_at'] is None or store.clock()<outbox['processed_at']+RETENTION
                        or outbox['hold'] or outbox['error'] or current_status['control_receipt']['pending']):
                    raise Refusal('shared and local whole processing+24h/transport/control remains held')
                if any(n['delivery_state']!='acknowledged' for n in material['notices']):
                    raise Refusal('every original transport claim must be actually settled')
                if material['attachments'] or any(p['post_seq']!=row['post'] for p in material['thread_posts']):
                    raise Refusal('foreign reply/attachment custody is not this producer-owned output')
                if conn.execute('SELECT seq FROM posts WHERE reply_to=? LIMIT 1',(row['post'],)).fetchone():
                    raise Refusal('foreign addressed relationship retains its canonical pointer')
                if len(material['post'])!=1 or material['post'][0]['author']!=row['actor'] or material['post'][0]['ref']!='delivery:'+key:
                    raise Refusal('exact original producer-owned pointer required')
                witness={'original':current,'issuer':actor,'recipient_consent':dict(consent),'custody':receipt}
                raw=(encode(witness)+'\n').encode()
                from .store import owned_bytes
                held_bytes=owned_bytes(store.home/'shared-custody',store.config['limits'].get('max_files',50000)) if (store.home/'shared-custody').exists() else 0
                if archive.exists():
                    held_bytes-=archive.stat().st_size
                if (type(receipt['archive_budget_bytes']) is not int or type(receipt['archive_existing_bytes']) is not int
                        or receipt['archive_existing_bytes']!=held_bytes or held_bytes+len(raw)>receipt['archive_budget_bytes']):
                    raise Refusal('accountable cumulative custody budget full; never hide obligations by moving them')
                store.budget(None,len(raw)+4096)
                archive.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                try:
                    with archive.open('xb') as stream:
                        os.chmod(archive,0o600); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                except FileExistsError:
                    if regular_path(str(archive)).read_bytes()!=raw:
                        raise Refusal('interrupted canonical conservation differs; keep both and do not replay')
                directory_fd=os.open(archive.parent,os.O_RDONLY|os.O_DIRECTORY)
                try: os.fsync(directory_fd)
                finally: os.close(directory_fd)
                info=store.path.stat(); frontier=(str(store.path),info.st_dev,info.st_ino,row['actor'])
                previous=conn.execute('SELECT * FROM coordinator_scan_frontiers_v1 WHERE runtime=? AND device=? AND inode=? AND actor=?',frontier).fetchone()
                chain=digest({'previous':previous['chain'] if previous else None,'witness':digest(witness)})
                conn.execute('INSERT INTO coordinator_scan_frontiers_v1 VALUES(?,?,?,?,?,?,?) ON CONFLICT(runtime,device,inode,actor) DO UPDATE SET through=MAX(through,excluded.through),count=count+1,chain=excluded.chain',
                             (*frontier,row['post'],1,chain))
                self.store.retire_coordinator_pointer(conn,key,actor,{'basis':current['basis'],'archive_hash':digest(witness),'recipient':row['recipient'],'evidence':receipt['evidence']})
                for table in ('coordinator_software_deliveries_v1','coordinator_owner_return_checks_v1','coordinator_owner_corrections_v1','coordinator_custody_consents_v1'):
                    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                        conn.execute(f'DELETE FROM {table} WHERE delivery=?',(key,))
                conn.execute('DELETE FROM coordinator_deliveries_v1 WHERE id=?',(key,))
        # Caller must conserve this return. Crash after the shared commit leaves
        # the archived witness; reconciliation observes absence, never reposts.
        result={'delivery':key,'canonical_archive':str(archive),'archive_hash':digest(witness),'scan_chain':chain,
                'conserved_at':store.clock(),
                'meaning':'qualified owned shared rows/pointer retired; required full envelope retained in accountable custody; no platform-store reclamation'}
        with store.tx():
            store.db.execute("UPDATE shared_custody_intents SET state='retired',receipt=? WHERE delivery=?",(encode(result),key))
        return result

    def reconcile_shared_custody(self,store,key):
        """Resolve a lost local return from exact archived source and shared absence."""
        self.store.acting_session(store.config['software_delegation']['grantor'])
        intent=store.one('SELECT * FROM shared_custody_intents WHERE delivery=?',(key,))
        if not intent:
            raise Refusal('original shared retirement intent required')
        raw=regular_path(intent['archive']).read_text()
        witness=json.loads(raw)
        if witness['original']['basis']!=intent['basis'] or witness['original']['material']['delivery']['id']!=key:
            raise Refusal('exact conserved canonical witness required')
        with self.opened(settlement=True,owner_required=False) as conn:
            if conn.execute('SELECT id FROM coordinator_deliveries_v1 WHERE id=?',(key,)).fetchone():
                raise Refusal('shared commit not observed; original intent remains held, do not replay')
            info=store.path.stat()
            frontier=conn.execute('SELECT * FROM coordinator_scan_frontiers_v1 WHERE runtime=? AND device=? AND inode=? AND actor=?',
                                  (str(store.path),info.st_dev,info.st_ino,store.config['actor'])).fetchone()
            if not frontier or frontier['through']<witness['original']['material']['delivery']['post']:
                raise Refusal('shared scan conservation unobserved')
        if intent['state']=='retired' and intent['receipt']:
            return json.loads(intent['receipt'])
        # A lost return supplies no original completion clock. Use this actual
        # observation conservatively; repeated reconciliation preserves it.
        result={'delivery':key,'canonical_archive':intent['archive'],'archive_hash':digest(witness),
                'conserved_at':store.clock(),'meaning':'exact archived original/shared absence reconciled; no new send or original END inferred'}
        with store.tx():
            store.db.execute("UPDATE shared_custody_intents SET state='retired',receipt=? WHERE delivery=?",(encode(result),key))
        return result

    def release_shared_archive(self,store,key,receipt):
        """Actual custodian's qualified disposal of a conserved OWNED copy.

        Original source/result/history and canonical targets remain at their
        proper homes. This never classifies them disposable from their names.
        """
        actor=self.store.acting_session(store.config['software_delegation']['grantor'])
        intent=store.one("SELECT * FROM shared_custody_intents WHERE delivery=? AND state='retired'",(key,))
        if not intent or set(receipt)!={'hash','qualified_at','holds','evidence','originals','custodian','processing'}:
            raise Refusal('exact retired archive and actual original conservation/release required')
        path=regular_path(intent['archive']); witness=json.loads(path.read_text())
        fresh(store,{**receipt,'basis':receipt['hash']},digest(witness))
        conserved=json.loads(intent['receipt'] or '{}')
        processing=receipt['processing']
        completed=processing.get('completed_at') if isinstance(processing,dict) else None
        if (not isinstance(processing,dict) or set(processing)!={'completed_at','evidence'}
                or type(completed) not in {int,float} or not math.isfinite(completed)
                or type(conserved.get('conserved_at')) not in {int,float}
                or not math.isfinite(conserved['conserved_at'])
                or conserved.get('archive_hash')!=digest(witness)
                or not conserved['conserved_at']<=completed<=receipt['qualified_at']
                or store.clock()<completed+RETENTION):
            raise Refusal('new producer-owned archive copy needs its own completed conservation+24h frontier')
        required_text(processing['evidence'],'actual archive custodian/consumer processing completion evidence')
        expected={name:digest(value) for name,value in witness['original']['material'].items()}
        if receipt['custodian']!=witness['custody']['custodian'] or not isinstance(receipt['originals'],dict) or set(receipt['originals'])!=set(expected):
            raise Refusal('actual archive custodian and every required original conservation required')
        for name,proof in receipt['originals'].items():
            if not isinstance(proof,dict) or set(proof)!={'hash','custodian','evidence'} or proof['hash']!=expected[name]:
                raise Refusal('exact full original hashes and actual custodians required; no unnamed data loss')
            required_text(proof['custodian'],'actual original custodian'); required_text(proof['evidence'],'original conservation evidence')
        # Revalidate the exact identity immediately before this deliberately
        # selected copy removal. No canonical or foreign source is touched.
        info=path.stat(); raw=path.read_text()
        if digest(json.loads(raw))!=receipt['hash'] or path.stat()!=info:
            raise Refusal('owned archive changed; preserve it')
        path.unlink()
        return {'delivery':key,'archive':str(path),'removed_owned_copy':True,'actor':actor,'receipt':receipt,
                'original_witness':witness,'meaning':'full return remains with actual collecting custodian; no original source/target/profile reclamation'}
