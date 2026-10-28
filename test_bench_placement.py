"""Exercise actual placement parsing with DWARF records and the failed RV32 ELF."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent


def attr(value, form='DW_FORM_addr'):
    return SimpleNamespace(value=value, form=form)


class Die:
    serial = 0

    def __init__(self, tag, attributes=None, parent=None, origin=None):
        Die.serial += 1
        self.offset = Die.serial
        self.tag, self.attributes, self.parent = tag, attributes or {}, parent
        self.origin = origin
        self.cu = None

    def get_parent(self):
        return self.parent

    def get_DIE_from_attribute(self, name):
        if self.origin is None:
            raise ValueError('Broken origin reference')
        return self.origin


class Elf:
    def __init__(self, dies=(), ranges=(), symbols=None, base=0, dwarf=True):
        self.dies, self.entries, self.symbols = list(dies), list(ranges), symbols or {}
        self.top = Die('DW_TAG_compile_unit', {'DW_AT_low_pc': attr(base)} if base is not None else {})
        self.available = dwarf
        for die in self.dies:
            die.cu = self
            if die.parent:
                die.parent.cu = self

    def get_section_by_name(self, name):
        symbols = [SimpleNamespace(name=n, entry=SimpleNamespace(st_value=v, st_size=16))
                   for n, v in self.symbols.items()]
        return SimpleNamespace(iter_symbols=lambda: iter(symbols))

    def has_dwarf_info(self, strict=False):
        return self.available

    def get_dwarf_info(self):
        return self

    def iter_CUs(self):
        return iter([self])

    def iter_DIEs(self):
        return iter(self.dies)

    def get_top_DIE(self):
        return self.top

    def range_lists(self):
        return self

    def get_range_list_at_offset(self, offset, cu=None):
        return self.entries


def relative(start, end):
    return SimpleNamespace(begin_offset=start, end_offset=end, is_absolute=False)


def absolute(start, end):
    return SimpleNamespace(begin_offset=start, end_offset=end, is_absolute=True)


def inline_elf(entries=None, attributes=None, name=b'executeBytecodeInstructions', caller=b'VM_executeCode', base=0):
    owner = Die('DW_TAG_subprogram', {'DW_AT_name': attr(caller, 'DW_FORM_string'),
                'DW_AT_low_pc': attr(0x10400000), 'DW_AT_high_pc': attr(0x1000, 'DW_FORM_data4')})
    origin = Die('DW_TAG_subprogram', {'DW_AT_name': attr(name, 'DW_FORM_string')})
    fields = {'DW_AT_abstract_origin': attr(1, 'DW_FORM_ref4'),
              'DW_AT_ranges': attr(0, 'DW_FORM_sec_offset'), 'DW_AT_entry_pc': attr(0x10400020)}
    if attributes is not None:
        fields = attributes
    inline = Die('DW_TAG_inlined_subroutine', fields, parent=owner, origin=origin)
    return Elf([owner, origin, inline], entries if entries is not None else [absolute(0x10400020, 0x10400040)], base=base)


class PlacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((ROOT / 'bench/rtl.py').read_text())
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == 'prepare':
                    break
                if node.name not in ['sha', 'save']:
                    functions.append(node)
        cls.namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), 'bench/rtl.py', 'exec'), cls.namespace)

    def placement(self, elf, variant='sdram', current=True):
        function = self.namespace.get('interpreter_placement')
        self.assertIsNotNone(function, 'Placement resolver must handle concrete inline DWARF')
        return function(elf, variant, current)

    def test_relative_ranges_resolve_cu_and_selected_bases(self):
        elf = inline_elf([relative(0x20, 0x40), SimpleNamespace(base_address=0x10400100), relative(0, 0x30)], base=0x10400000)
        result = self.placement(elf)
        self.assertEqual(result['kind'], 'inline')
        self.assertEqual(result['entry'], 0x10400020)
        self.assertEqual(result['ranges'], [[0x10400020, 0x10400040], [0x10400100, 0x10400130]])

    def test_absolute_ranges_ignore_cu_base(self):
        result = self.placement(inline_elf(base=0x70000000))
        self.assertEqual(result['ranges'], [[0x10400020, 0x10400040]])

    def test_low_high_pc_accept_address_and_constant_forms(self):
        for high in [attr(0x10400040), attr(0x20, 'DW_FORM_data4')]:
            with self.subTest(form=high.form):
                fields = {'DW_AT_abstract_origin': attr(1, 'DW_FORM_ref4'),
                          'DW_AT_low_pc': attr(0x10400020), 'DW_AT_high_pc': high}
                result = self.placement(inline_elf(attributes=fields))
                self.assertEqual(result['entry'], 0x10400020)
                self.assertEqual(result['ranges'], [[0x10400020, 0x10400040]])

    def test_missing_dwarf_or_matching_inline_is_rejected(self):
        for elf in [Elf(dwarf=False), Elf(), inline_elf(name=b'unrelated'),
                    inline_elf(caller=b'unrelated')]:
            with self.subTest(elf=elf):
                with self.assertRaises(RuntimeError):
                    self.placement(elf)

    def test_legacy_and_bram_never_accept_inline_fallback(self):
        for current, variant in [(False, 'sdram'), (True, 'bram'), (False, 'bram')]:
            with self.subTest(current=current, variant=variant):
                with self.assertRaises(RuntimeError):
                    self.placement(inline_elf(), current=current, variant=variant)

    def test_symbol_selection_remains_strict(self):
        self.assertEqual(self.placement(Elf(symbols={'executeLoop': 0x4000}), 'bram', False)['entry'], 0x4000)
        for symbols, variant in [({'executeLoop': 0x4000, 'executeBytecodeInstructions': 0x5000}, 'bram'),
                                 ({'executeBytecodeInstructions': 0x10400000}, 'bram'),
                                 ({'executeBytecodeInstructions': 0x4000}, 'sdram')]:
            with self.subTest(symbols=symbols, variant=variant):
                with self.assertRaises(RuntimeError):
                    self.placement(Elf(symbols=symbols), variant)

    def test_malformed_empty_inverted_and_mixed_outside_ranges_reject(self):
        cases = [[], [object()], [relative(0, 0)], [relative(8, 4)],
                 [absolute(0x10400020, 0x10400040), absolute(0x10800000, 0x10800002)],
                 [absolute(0x103ffffe, 0x10400004)], [absolute(0x107ffffe, 0x10800002)],
                 [SimpleNamespace(base_address=-1), relative(0, 4)],
                 [SimpleNamespace(begin_offset='bad', end_offset=4, is_absolute=True)],
                 [absolute(0x10400020, 0x10400040), absolute(0x10400030, 0x10400050)]]
        for entries in cases:
            with self.subTest(entries=entries):
                with self.assertRaises(RuntimeError):
                    self.placement(inline_elf(entries))

    def test_relative_ranges_require_a_resolved_base(self):
        with self.assertRaises(RuntimeError):
            self.placement(inline_elf([relative(0, 4)], base=None))

    def test_entry_must_be_inside_a_concrete_range(self):
        elf = inline_elf()
        elf.dies[-1].attributes['DW_AT_entry_pc'] = attr(0x10400050)
        with self.assertRaises(RuntimeError):
            self.placement(elf)

    def test_non_address_entry_and_cu_base_forms_are_rejected(self):
        for field in ['entry', 'base']:
            elf = inline_elf()
            if field == 'entry':
                elf.dies[-1].attributes['DW_AT_entry_pc'] = attr(0x10400020, 'DW_FORM_ref4')
            else:
                elf.top.attributes['DW_AT_low_pc'] = attr(0x10400000, 'DW_FORM_data4')
            with self.subTest(field=field):
                with self.assertRaises(RuntimeError):
                    self.placement(elf)

    def test_broken_or_cyclic_origin_is_rejected(self):
        for cyclic in [False, True]:
            elf = inline_elf()
            elf.dies[-1].origin = elf.dies[-1] if cyclic else None
            with self.subTest(cyclic=cyclic):
                with self.assertRaises(RuntimeError):
                    self.placement(elf)

    def test_inline_ranges_must_belong_to_named_caller(self):
        with self.assertRaises(RuntimeError):
            self.placement(inline_elf([absolute(0x10400020, 0x10400040), absolute(0x10402000, 0x10402020)]))

    def test_ambiguous_multiple_inline_instances_are_rejected(self):
        elf = inline_elf()
        second = Die('DW_TAG_inlined_subroutine', dict(elf.dies[-1].attributes), elf.dies[0], elf.dies[1])
        second.cu = elf
        elf.dies.append(second)
        with self.assertRaises(RuntimeError):
            self.placement(elf)

    def test_real_failed_published_elf_resolves_positive_inline_ranges(self):
        try:
            from elftools.elf.elffile import ELFFile
        except ImportError:
            self.skipTest('pyelftools required; actual ELF check also runs in isolated toolchain')
        path = ROOT / 'experiments/cases/release-v077-3b9fcfd5-deltarune-dodge-accuracy-trace-699614e3d770f44a/build/fullframe/deltarune/sdram/program.elf'
        if not path.exists():
            self.skipTest('Optional private failed published ELF is absent')
        with path.open('rb') as stream:
            result = self.placement(ELFFile(stream))
        self.assertEqual(result['kind'], 'inline')
        self.assertEqual(result['entry'], 0x1044abc0)
        self.assertEqual(len(result['ranges']), 9)
        self.assertEqual(result['ranges'][0], [0x1044abc0, 0x1044ae14])
        self.assertEqual(result['ranges'][-1], [0x1044c508, 0x1044c5a8])


if __name__ == '__main__':
    unittest.main()
