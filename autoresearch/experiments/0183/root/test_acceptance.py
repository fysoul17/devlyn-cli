from test_support import Base, FILES

class Root(Base):
    def test_absolute_and_relative_root(self):
        other = self.base/'다른 checkout'
        self.populate(other)
        (other/'AGENTS.md').write_text('different root text\n',encoding='utf-8')
        a = self.report('--root',str(other))
        b = self.report('--root',other.name,cwd=self.base)
        self.assertEqual(a,b)
        self.assertNotEqual(a,self.report())
        self.check_totals(a)
        paths = [f['path'] for s in a['skills']+[a['root'],a['shared']] for f in s['files']]
        self.assertEqual(set(paths),set(FILES))

    def test_existing_root_equivalence(self):
        self.assertEqual(self.cli().stdout,self.cli('--root',str(self.home)).stdout)
        self.assertEqual(self.report(),self.report('--root',str(self.home)))

    def test_empty_root(self):
        empty = self.base/'empty'; empty.mkdir()
        data = self.report('--root',str(empty))
        self.assertEqual(data['skills'],[])
        self.assertEqual(data['root']['files'],[])
        self.assertEqual(data['shared']['files'],[])
        self.assertTrue(all(v==0 for v in data['grand_total'].values()))
        result=self.cli('--root',str(empty))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('GRAND TOTAL',result.stdout)
        self.assertNotIn('Alpha',result.stdout)

    def test_invalid_roots(self):
        self.bad('--root',str(self.base/'missing'))
        self.bad('--json','--root',str(self.script))

    def test_help(self):
        result=self.cli('--help')
        self.assertEqual(result.returncode,0)
        self.assertIn('--root',result.stdout)
