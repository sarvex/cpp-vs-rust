#!/usr/bin/env python

import pathlib
import re
import shutil
import subprocess
import typing

ROOT = pathlib.Path(__file__).parent / ".."

macros = [
    "assert_matches",
    "qljs_always_assert",
    "qljs_assert",
    "qljs_assert_diags",
    "qljs_assert_no_diags",
    "qljs_c_string",
    "qljs_case_contextual_keyword",
    "qljs_case_reserved_keyword",
    "qljs_case_reserved_keyword_except_await_and_function_and_yield",
    "qljs_case_reserved_keyword_except_await_and_yield",
    "qljs_case_strict_only_reserved_keyword",
    "qljs_case_strict_reserved_keyword",
    "qljs_case_typescript_only_contextual_keyword_except_type",
    "qljs_const_assert",
    "qljs_crash_allowing_core_dump",
    "qljs_match_diag_field",
    "qljs_case_binary_only_operator_symbol_except_less_less_and_star",
    "qljs_case_binary_only_operator_symbol_except_star",
    "qljs_case_binary_only_operator_symbol_except_star",
    "qljs_case_binary_only_operator_symbol",
    "qljs_case_compound_assignment_operator_except_slash_equal",
    "qljs_case_binary_only_operator_symbol",
    "qljs_match_diag_fields",
    "qljs_never_assert",
    "qljs_offset_of",
    "qljs_slow_assert",
    "qljs_translatable",
    "scoped_trace",
]


def main() -> None:
    project_dir = ROOT / "rust-threecrate-cratecargotest"
    new_project_from_template(project_dir, template_dir=ROOT / "rust")
    workspace_to_threecrate(project_dir)
    fix_cargo_lock(project_dir)

    project_dir = ROOT / "rust-workspace-crateunotest"
    new_project_from_template(project_dir, template_dir=ROOT / "rust")
    cargotest_to_unotest(project_dir)
    fix_cargo_lock(project_dir)

    project_dir = ROOT / "rust-workspace-cratecargotest-nodefaultfeatures"
    new_project_from_template(project_dir, template_dir=ROOT / "rust")
    disable_default_crate_features(project_dir)
    fix_cargo_lock(project_dir)

    project_dir = ROOT / "rust-twocrate-cratecargotest"
    new_project_from_template(project_dir, template_dir=ROOT / "rust")
    workspace_to_twocrate(project_dir)
    fix_cargo_lock(project_dir)

    project_dir = ROOT / "rust-twocrate-unittest"
    new_project_from_template(
        project_dir, template_dir=ROOT / "rust-twocrate-cratecargotest"
    )
    cargotest_to_unittest(project_dir)
    fix_cargo_lock(project_dir)

    project_dir = ROOT / "rust-threecrate-crateunotest"
    new_project_from_template(
        project_dir, template_dir=ROOT / "rust-threecrate-cratecargotest"
    )
    cargotest_to_unotest(project_dir)
    fix_cargo_lock(project_dir)

    for total_copies in (8, 16, 24):
        project_dir = ROOT / f"rust-workspace-cratecargotest-{total_copies}"
        new_project_from_template(project_dir, template_dir=ROOT / "rust")
        multiply_lex_module_rs(project_dir, total_copies=total_copies)
        fix_cargo_lock(project_dir)

    for total_copies in (8, 16, 24):
        project_dir = ROOT / f"cpp-{total_copies}"
        new_project_from_template(project_dir, template_dir=ROOT / "cpp")
        multiply_lex_module_cpp(project_dir, total_copies=total_copies)


def new_project_from_template(
    project_dir: pathlib.Path, template_dir: pathlib.Path
) -> None:
    delete_dir(project_dir)
    shutil.copytree(template_dir, project_dir, symlinks=True)
    (project_dir / "README").write_text(
        "THIS PROJECT WAS GENERATED BY generate-rust-project.py\n"
    )


def cargotest_to_unotest(project_dir: pathlib.Path) -> None:
    tests_dirs = list(project_dir.glob("**/tests"))
    for test_dir in tests_dirs:
        mod_dir = test_dir / "t"
        mod_dir.mkdir(exist_ok=False)

        mod_file = ""
        for test_file in sorted(test_dir.glob("test_*.rs")):
            test_file.rename(mod_dir / test_file.name)
            mod_file += f"mod {test_file.stem};\n"

        (test_dir / "test.rs").write_text(f"mod {mod_dir.name};\n")
        (mod_dir / "mod.rs").write_text(mod_file)


def workspace_to_twocrate(project_dir: pathlib.Path) -> None:
    workspace_to_fewcrate(project_dir, libs_to_keep=("proc_diagnostic_types",))


def workspace_to_threecrate(project_dir: pathlib.Path) -> None:
    workspace_to_fewcrate(project_dir, libs_to_keep=("proc_diagnostic_types", "test"))


def workspace_to_fewcrate(
    project_dir: pathlib.Path, libs_to_keep: typing.Tuple[str, ...]
) -> None:
    crate_dirs = sorted(d for d in project_dir.glob("libs/*"))
    crate_names = [d.name for d in crate_dirs]

    def fix_rs(rs: pathlib.Path, current_crate_name: str, crate_reference: str) -> None:
        source = rs.read_text()
        if current_crate_name not in libs_to_keep:
            source = source.replace("crate::", f"cpp_vs_rust_{current_crate_name}::")
        for crate_name in crate_names:
            if crate_name in libs_to_keep:
                continue
            for macro in macros:
                source = source.replace(
                    f"cpp_vs_rust_{crate_name}::{macro}", f"{crate_reference}::{macro}"
                )
            source = source.replace(
                f"cpp_vs_rust_{crate_name}::", f"{crate_reference}::{crate_name}::"
            )
        source = source.replace(
            "\n        use crate::qljs_crash_allowing_core_dump;\n",
            "\n        use $crate::qljs_crash_allowing_core_dump;\n",
        )
        rs.write_text(source)

    for crate_dir in crate_dirs:
        crate_name = crate_dir.name

        if crate_name in libs_to_keep:
            for src in crate_dir.glob("src/*.rs"):
                fix_rs(src, crate_name, "cpp_vs_rust")
            for src in crate_dir.glob("tests/*.rs"):
                fix_rs(src, crate_name, "cpp_vs_rust")
        else:
            new_src_dir = project_dir / "src" / crate_name
            new_src_dir.mkdir(exist_ok=True, parents=True)
            for src in crate_dir.glob("src/*.rs"):
                fix_rs(src, crate_name, "crate")
                src.rename(new_src_dir / src.name)

            new_tests_dir = project_dir / "tests"
            new_tests_dir.mkdir(exist_ok=True, parents=True)
            for test in crate_dir.glob("tests/*.rs"):
                fix_rs(test, crate_name, "cpp_vs_rust")
                test.rename(new_tests_dir / test.name)

            (new_src_dir / "lib.rs").rename(new_src_dir / "mod.rs")

    if "test" in libs_to_keep:
        cargo_toml_path = project_dir / "libs" / "test" / "Cargo.toml"
        cargo_toml = cargo_toml_path.read_text()
        for crate_name in crate_names:
            cargo_toml = cargo_toml.replace(
                f'cpp_vs_rust_{crate_name} = {{ path = "../{crate_name}" }}\n', ""
            )
        cargo_toml = cargo_toml.replace(
            "[dependencies]\n", '[dependencies]\ncpp_vs_rust = { path = "../.." }\n'
        )
        cargo_toml_path.write_text(cargo_toml)

    lib_rs = ""
    for crate_name in crate_names:
        if crate_name not in libs_to_keep:
            lib_rs += f"pub mod {crate_name};\n"

    (project_dir / "src" / "lib.rs").write_text(lib_rs)

    dependencies = ""
    dev_dependencies = ""
    for lib_to_keep in libs_to_keep:
        line = f'cpp_vs_rust_{lib_to_keep} = {{ path = "libs/{lib_to_keep}" }}\n'
        if lib_to_keep == "test":
            dev_dependencies += line
        else:
            dependencies += line
    if "test" not in libs_to_keep:
        dependencies += '\nlazy_static = { version = "1.4.0" }\n'

    cargo_toml_path = project_dir / "Cargo.toml"
    cargo_toml = cargo_toml_path.read_text()
    cargo_toml = f"""\
[package]
name = "cpp_vs_rust"
version = "0.1.0"
edition = "2021"

[workspace]
members = [ {",".join(f'"libs/{c}"' for c in libs_to_keep)} ]

[lib]
crate-type = ["cdylib", "lib"]
doctest = false
test = false

[dependencies]
{dependencies}
libc = {{ version = "0.2.138", default-features = false }}

[dev-dependencies]
{dev_dependencies}
memoffset = {{ version = "0.7.1" }}

[features]
default = []
qljs_debug = []

{cargo_toml[cargo_toml.index("[profile"):]}"""
    cargo_toml_path.write_text(cargo_toml)


def cargotest_to_unittest(project_dir: pathlib.Path) -> None:
    test_files = sorted(project_dir.glob("tests/test_*.rs"))

    for test_file in test_files:
        test_file.write_text(test_file.read_text().replace(f"cpp_vs_rust::", "crate::"))
        test_file.rename(project_dir / "src" / test_file.name)

    mod_file = ""
    for test_file in test_files:
        mod_file += f"#[cfg(test)]\nmod {test_file.stem};\n"
    lib_rs = project_dir / "src" / "lib.rs"
    lib_rs.write_text(lib_rs.read_text() + "\n" + mod_file)

    cargo_toml_path = project_dir / "Cargo.toml"
    cargo_toml = cargo_toml_path.read_text()
    cargo_toml = cargo_toml.replace("\ntest = false\n", "\n")
    cargo_toml_path.write_text(cargo_toml)

    (project_dir / "tests").rmdir()


def disable_default_crate_features(project_dir: pathlib.Path) -> None:
    did_update_cargo_toml = False
    for cargo_toml_path in project_dir.glob("**/Cargo.toml"):
        cargo_toml = cargo_toml_path.read_text()
        updated_cargo_toml = cargo_toml.replace(
            'libc = { version = "0.2.138" }',
            'libc = { version = "0.2.138", default-features = false }',
        )
        if updated_cargo_toml == cargo_toml:
            continue
        did_update_cargo_toml = True
        cargo_toml_path.write_text(updated_cargo_toml)
    assert did_update_cargo_toml, "Cargo.toml should have changed"


def multiply_lex_module_rs(project_dir: pathlib.Path, total_copies: int) -> None:
    assert total_copies > 1

    original_test_lex_rs = project_dir / "libs" / "fe" / "tests" / "test_lex.rs"
    original_test_lex_rs_code = original_test_lex_rs.read_text()
    for i in range(1, total_copies):
        new_test_lex_rs = (
            original_test_lex_rs.parent / f"{original_test_lex_rs.stem}_{i}.rs"
        )
        new_test_lex_rs.write_text(
            original_test_lex_rs_code.replace("::lex::", f"::lex_{i}::")
        )

    original_lex_rs = project_dir / "libs" / "fe" / "src" / "lex.rs"
    original_lex_rs_code = original_lex_rs.read_text()
    for i in range(1, total_copies):
        new_lex_rs = original_lex_rs.parent / f"{original_lex_rs.stem}_{i}.rs"
        new_lex_rs.write_text(original_lex_rs_code)

    new_mods = "pub mod lex;\n"
    for i in range(1, total_copies):
        new_mods += f"pub mod lex_{i};\n"
    lib_rs = project_dir / "libs" / "fe" / "src" / "lib.rs"
    lib_rs.write_text(lib_rs.read_text().replace("pub mod lex;\n", new_mods))


def multiply_lex_module_cpp(project_dir: pathlib.Path, total_copies: int) -> None:
    assert total_copies > 1

    def fix_source(source: str, i: int) -> str:
        return re.sub(
            r"\b(lexer(_transaction)?|test_lex)\b",
            lambda math: f"{math.group(0)}_{i}",
            source,
        ).replace("quick-lint-js/fe/lex.h", f"quick-lint-js/fe/lex-{i}.h")

    original_test_lex_cpp = project_dir / "test" / "test-lex.cpp"
    original_test_lex_cpp_code = original_test_lex_cpp.read_text()
    for i in range(1, total_copies):
        new_test_lex_cpp = (
            original_test_lex_cpp.parent / f"{original_test_lex_cpp.stem}-{i}.cpp"
        )
        new_test_lex_cpp.write_text(fix_source(original_test_lex_cpp_code, i=i))

    original_lex_cpp = project_dir / "src" / "quick-lint-js" / "fe" / "lex.cpp"
    original_lex_cpp_code = original_lex_cpp.read_text()
    for i in range(1, total_copies):
        new_lex_cpp = original_lex_cpp.parent / f"{original_lex_cpp.stem}-{i}.cpp"
        new_lex_cpp.write_text(fix_source(original_lex_cpp_code, i=i))

    original_lex_h = project_dir / "src" / "quick-lint-js" / "fe" / "lex.h"
    original_lex_h_code = original_lex_h.read_text()
    for i in range(1, total_copies):
        new_lex_h = original_lex_h.parent / f"{original_lex_h.stem}-{i}.h"
        new_lex_h.write_text(fix_source(original_lex_h_code, i=i))

    original_src_files = "  quick-lint-js/fe/lex.cpp\n  quick-lint-js/fe/lex.h"
    new_src_files = original_src_files
    for i in range(1, total_copies):
        new_src_files += (
            f"\n  quick-lint-js/fe/lex-{i}.cpp\n  quick-lint-js/fe/lex-{i}.h"
        )
    src_cmakelists_txt = project_dir / "src" / "CMakeLists.txt"
    src_cmakelists_txt.write_text(
        src_cmakelists_txt.read_text().replace(original_src_files, new_src_files)
    )

    original_test_files = "  test-lex.cpp"
    new_test_files = original_test_files
    for i in range(1, total_copies):
        new_test_files += f"\n  test-lex-{i}.cpp"
    test_cmakelists_txt = project_dir / "test" / "CMakeLists.txt"
    test_cmakelists_txt.write_text(
        test_cmakelists_txt.read_text().replace(original_test_files, new_test_files)
    )


def fix_cargo_lock(project_dir: pathlib.Path) -> None:
    subprocess.check_call(["cargo", "fetch"], cwd=project_dir)


def delete_dir(dir: pathlib.Path) -> None:
    try:
        shutil.rmtree(dir)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    main()
