import json
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal as D
from scripts.report import read_report, ReportError
from scripts.audit import audit_jtl
from scripts.contracts import TaskSpec, Phase


def make_report(root, *, pct_titles=None, count=4, errors=0, error_pct=0, tps=100, p90=500, label='target'):
    root=Path(root); (root/'content/js').mkdir(parents=True,exist_ok=True)
    titles=['Label','#Samples','FAIL','Error %','Average','Min','Max','Median']+(pct_titles or ['90th pct','95th pct','99th pct'])+['Transactions/s','Received','Sent']
    row={'transaction':label,'sampleCount':count,'errorCount':errors,'errorPct':error_pct,'throughput':tps,'pct1ResTime':p90,'pct2ResTime':p90+100,'pct3ResTime':p90+200}
    (root/'statistics.json').write_text(json.dumps({label:row,'Total':dict(row,transaction='Total',sampleCount=999)}),encoding='utf-8')
    table={'titles':titles,'items':[{'data':[label,count,errors,error_pct,1,1,1,1,p90,p90+100,p90+200,tps,0,0],'isController':False}]}
    (root/'content/js/dashboard.js').write_text('createTable($("#statisticsTable"), '+json.dumps(table)+', function(){});',encoding='utf-8')
    (root/'index.html').write_text('<table id="generalInfos"><tr><td>Start Time</td><td>"9/20/26, 8:00 PM"</td></tr><tr><td>End Time</td><td>"9/20/26, 8:02 PM"</td></tr></table>',encoding='utf-8')


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);make_report(self.root)

    def test_official_values_and_time(self):
        m=read_report(self.root,'target')
        self.assertEqual((m.sample_count,m.tps,m.p90_ms),(4,D(100),D(500)))
        self.assertEqual(m.start_time,'"9/20/26, 8:00 PM"')
        self.assertEqual(len(m.evidence['hashes']),3)

    def test_nondefault_percentiles(self):
        make_report(self.root,pct_titles=['80th pct','90th pct','99th pct'])
        m=read_report(self.root,'target')
        self.assertEqual(m.p90_ms,D(600));self.assertEqual(m.evidence['p90_field'],'pct2ResTime')

    def test_no_p90_unreadable(self):
        make_report(self.root,pct_titles=['80th pct','95th pct','99th pct'])
        with self.assertRaises(ReportError):read_report(self.root,'target')

    def test_total_or_absent_rejected(self):
        for label in ['Total','absent']:
            with self.subTest(label=label),self.assertRaises(ReportError):read_report(self.root,label)

    def test_quality_boundary(self):
        task=TaskSpec('task','id',(50,500),(50,100,200,500),50,D('.005'),D(2500))
        make_report(self.root,count=200,errors=1,error_pct=.5,p90=2500)
        self.assertTrue(read_report(self.root,'target').observation(task,1,Phase.COARSE,50).is_qualified)
        make_report(self.root,p90=2500.1)
        self.assertFalse(read_report(self.root,'target').observation(task,1,Phase.COARSE,50).is_qualified)

    def test_audit_does_not_override(self):
        m=read_report(self.root,'target')
        jtl=self.root/'data.jtl';jtl.write_text('label,success\ntarget,false\nprerequisite,true\n',encoding='utf-8')
        result=audit_jtl(jtl,m,comparison_profile='same-label-unfiltered')
        self.assertEqual(result['status'],'warning');self.assertFalse(result['changes_scoring'])
        self.assertEqual(m.error_percent,D(0));self.assertEqual(m.sample_count,4)

    def test_duplicate_row_rejected(self):
        p=self.root/'content/js/dashboard.js';text=p.read_text()
        table=json.JSONDecoder().raw_decode(text.split(', ',1)[1])[0]
        table['items']*=2;p.write_text('createTable($("#statisticsTable"), '+json.dumps(table))
        with self.assertRaises(ReportError):read_report(self.root,'target')

    def test_missing_or_nonfinite_not_zero(self):
        p=self.root/'statistics.json';rows=json.loads(p.read_text());rows['target']['throughput']='NaN';p.write_text(json.dumps(rows))
        with self.assertRaises(ReportError):read_report(self.root,'target')

    def test_inconsistent_official_fields_warn_only(self):
        make_report(self.root,count=4,errors=1,error_pct=0)
        m=read_report(self.root,'target')
        self.assertTrue(m.warnings);self.assertEqual(m.error_percent,0)

    def test_unknown_version(self):
        with self.assertRaises(ReportError):read_report(self.root,'target','6.0')

    def test_normal_float_representation_is_not_warning(self):
        make_report(self.root,count=6154,errors=95,error_pct=1.5437114)
        p=self.root/'content/js/dashboard.js'
        p.write_text(p.read_text(encoding='utf-8').replace('1.5437114','1.5437114072148196'),encoding='utf-8')
        self.assertEqual(read_report(self.root,'target').warnings,())

    def test_filter_is_not_comparable(self):
        p=self.root/'index.html'
        p.write_text(p.read_text(encoding='utf-8').replace('</table>','<tr><td>Filter for display</td><td>target.*</td></tr></table>'),encoding='utf-8')
        self.assertEqual(audit_jtl(self.root/'missing.jtl',read_report(self.root,'target'))['status'],'not-comparable')

    def test_unknown_scope_does_not_claim_error(self):
        p=self.root/'data.jtl';p.write_text('label,success\ntarget,true\n',encoding='utf-8')
        result=audit_jtl(p,read_report(self.root,'target'))
        self.assertEqual(result['status'],'not-comparable')
        self.assertIn('do not prove',result['findings'][-1])


if __name__=='__main__':unittest.main()
