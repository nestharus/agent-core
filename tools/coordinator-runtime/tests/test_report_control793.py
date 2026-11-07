import unittest,copy,sqlite3,json
from types import SimpleNamespace
from coordinator_runtime import report_repair as r
from coordinator_runtime.contracts import Refusal,encode
class Boundaries(unittest.TestCase):
 def test_closed_exact_delta_and_v1_unchanged(self):
  root='/release'; prefix=root+'/tools/coordinator-runtime/coordinator_runtime/'
  old={n:'old' for n in r.PAIR_MODULES|r.SOURCE_MODULES}; new=copy.deepcopy(old);new['processing.py']='new'
  a={'root':root,'files':{prefix+n:v for n,v in old.items()}};b={'root':root,'files':{prefix+n:v for n,v in new.items()}}
  self.assertEqual(r.source_compatible(a,b,old,new,['processing.py'],_ceiling=r.PAIR_MODULES),[prefix+'processing.py'])
  with self.assertRaises(Refusal):r.source_compatible(a,b,old,new,['processing.py'])
  for module in ['configuration.py','model.py','runtime.py','template.md']:
   bad={**new,module:'bad'}; bb=copy.deepcopy(b);bb['files'][prefix+module]='bad'
   with self.assertRaises(Refusal):r.source_compatible(a,bb,old,bad,sorted(['processing.py',module]),_ceiling=r.PAIR_MODULES)
  for field in ['root','pool','policy']:
   bb={**b,field:'swapped'}
   with self.assertRaises(Refusal):r.source_compatible(a,bb,old,new,['processing.py'],_ceiling=r.PAIR_MODULES)
  bb=copy.deepcopy(b);bb['files']['/template']='changed'
  with self.assertRaises(Refusal):r.source_compatible(a,bb,old,new,['processing.py'],_ceiling=r.PAIR_MODULES)
 def test_original_deadlines_never_renewed(self):
  rt=SimpleNamespace(clock=lambda:1000.)
  for name in ['admission','wake','allocations','legacy_resources']:
   for field in ['expires','until']:
    for end in [999.,1000.,float('nan'),float('inf'),'later']:
     with self.assertRaises(Refusal):r.pair_finite(rt,{'service':{name:{field:end}}})
  r.pair_finite(rt,{'service':{'admission':{'until':1001.},'wake':{'until':1001.}}})
 def test_repair_selection_append_only(self):
  db=sqlite3.connect(':memory:');db.executescript(r.SCHEMA)
  db.execute('INSERT INTO same_authority_report_control_repairs_v2 VALUES(?,?,?,?)',('cap','{}','Work',1000.))
  for query in ['UPDATE same_authority_report_control_repairs_v2 SET request=1','DELETE FROM same_authority_report_control_repairs_v2']:
   with self.assertRaises(sqlite3.IntegrityError):db.execute(query)
  self.assertEqual(db.execute('SELECT request FROM same_authority_report_control_repairs_v2').fetchone()[0],'{}')
