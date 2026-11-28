"""Fast regression guard; static checks are not proof of runtime safety."""
import ast, importlib.util, pathlib, re, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Shipping(unittest.TestCase):
    def test_worker_no_shell_or_installer(self):
        for p in ROOT.joinpath('tools').glob('reconstruct-*.py'):
            ast.parse(p.read_text(encoding='utf-8-sig'))
            self.assertNotRegex(p.read_text(encoding='utf-8-sig'),r'(?i)(?:shell\s*=\s*True|\b(?:activate_plugin|wpmem_install_settings)\s*\()')
        text=ROOT.joinpath('tools/construction-worker.py').read_text();ast.parse(text)
        self.assertNotIn('shell=True',text);self.assertNotIn('os.system(',text)
        self.assertIn("'eval-file'",text)
    def test_admin_capability_and_nonce(self):
        text=ROOT.joinpath('src/ConstructionAdmin.php').read_text()
        self.assertIn("current_user_can('manage_options')",text)
        self.assertIn("check_admin_referer('ozeki_construction')",text)
        self.assertNotRegex(text,r'\b(?:shell_exec|exec|system|passthru|eval)\s*\(')
    def test_normal_table_validation_never_mutates_input(self):
        p=ROOT/'tools/reconstruct-tablepress.py';s=importlib.util.spec_from_file_location('shipping_table',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
        table={'name':'Values','description':'Numbers','data':[['001','42',r'C:\a\b']],'options':{},'visibility':{'rows':[1],'columns':[1,1,1]}}
        import copy
        before=copy.deepcopy(table);self.assertEqual(m.import_input(table),before);self.assertEqual(table,before)
        unsafe=copy.deepcopy(table);unsafe['options']['datatables_custom_commands']='alert(1)'
        with self.assertRaises(ValueError):m.import_input(unsafe)
        self.assertEqual(unsafe['options']['datatables_custom_commands'],'alert(1)')
    def test_existing_review_guards_remain_in_ci(self):
        text=ROOT.parents[1].joinpath('.github/workflows/contracts.yml').read_text()
        for name in ['no-software-install.php','workspace-boundary.php','startup-boundary.php','review-backup-write.php','review-media-cost.php','editor-nonce.php','prepared-settings.php']:
            self.assertIn(name,text)
if __name__=='__main__':unittest.main()
