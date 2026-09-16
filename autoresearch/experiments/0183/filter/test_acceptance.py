from test_support import Base

class Filter(Base):
    def test_exact_across_bases_and_totals(self):
        original=self.report()
        data=self.report('--skill','alpha')
        self.assertEqual([(s['base'],s['name']) for s in data['skills']],
            [('config/skills','alpha'),('optional-skills','alpha')])
        self.assertEqual(data['shared'],original['shared'])
        self.assertEqual(data['root'],original['root'])
        self.assertEqual(data['skills'],[s for s in original['skills'] if s['name']=='alpha'])
        self.check_totals(data)

    def test_case_sensitive_and_unknown(self):
        self.assertEqual([s['name'] for s in self.report('--skill','GAMMA')['skills']],['GAMMA'])
        self.bad('--skill','ALPHA')
        self.bad('--skill','alph')
        self.bad('--json','--skill','missing')
        self.bad('--skill','')

    def test_table(self):
        result=self.cli('--skill','alpha')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('alpha',result.stdout)
        self.assertNotIn('beta',result.stdout)
        self.assertNotIn('GAMMA',result.stdout)
        self.assertIn('_shared',result.stdout)
        self.assertIn('(root)',result.stdout)
        self.assertIn('GRAND TOTAL',result.stdout)

    def test_unfiltered(self):
        data=self.report()
        self.assertEqual([s['name'] for s in data['skills']],['alpha','beta','GAMMA','alpha'])
        self.check_totals(data)

    def test_help(self):
        result=self.cli('--help')
        self.assertEqual(result.returncode,0)
        self.assertIn('--skill',result.stdout)
