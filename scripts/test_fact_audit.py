#!/usr/bin/env python3
"""fact_audit.py 자체 점검 — 실행: python3 scripts/test_fact_audit.py

검증 목표: '이름만 팩트체크'로 되돌아가지 않는지 확인한다.
핵심은 네 방향이다.
  1. 원자료에 없는 수치는 반드시 잡힌다 (거짓 통과 없음)
  2. 원자료에 있는 수치는 통과한다 (모두 막는 게이트는 쓸모없다)
  3. 실행 위치(cwd)가 달라도 같은 원자료를 찾는다 (path-robust)
  4. 정량 수치는 파생본(archive_draft)만으로 통과하지 못한다 (순환 검증 차단)
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, "fact_audit.py")

SOURCE = """# 원자료
| 운영규모 | 목표 참여자 100명 / 실제 참여 인원 [확인 필요] / 사전 신청자 18명 |
- 기간: 2026. 4. 27.(월) 13:00 ~ 18:00
- 주최: 경북대학교 산학협력단
- 6개 프로그램 존 운영
"""


def run(draft_text, source_text=SOURCE):
    with tempfile.TemporaryDirectory() as d:
        draft = os.path.join(d, "x-2026-blog-draft.md")
        src = os.path.join(d, "src.md")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(draft_text)
        with open(src, "w", encoding="utf-8") as f:
            f.write(source_text)
        p = subprocess.run([sys.executable, AUDIT, draft, "--source", src],
                           capture_output=True, text=True)
        return p.returncode, p.stdout


ARCHIVE = """# 아카이브 초안 (파생본)
| 운영규모 | 총 참여자 243명 |
- 6개 존 동시 운영
"""


def build_project(d, draft_text, primary=None, derived=None, slug="x-2026"):
    """임시 프로젝트 트리(.claude/artifacts/...)를 만들고 초안 경로를 돌려준다."""
    arts = os.path.join(d, ".claude", "artifacts")
    for sub in ("blog_drafts", "fact_sources", "archive_drafts"):
        os.makedirs(os.path.join(arts, sub), exist_ok=True)
    draft = os.path.join(arts, "blog_drafts", f"{slug}-blog-draft.md")
    files = [(draft, draft_text)]
    if primary is not None:
        files.append((os.path.join(arts, "fact_sources", f"{slug}-source.md"), primary))
    if derived is not None:
        files.append((os.path.join(arts, "archive_drafts", f"{slug}-archive-draft.md"), derived))
    for path, text in files:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return draft


def run_auto(draft_text, primary=None, derived=None, cwd=None):
    """--source 없이 자동 탐색으로 실행한다. cwd 기본값은 프로젝트 루트가 아닌 곳."""
    with tempfile.TemporaryDirectory() as d:
        draft = build_project(d, draft_text, primary, derived)
        p = subprocess.run([sys.executable, AUDIT, draft], capture_output=True, text=True,
                           cwd=cwd or tempfile.gettempdir())
        return p.returncode, p.stdout + p.stderr


class TestFactAudit(unittest.TestCase):

    def test_fabricated_number_is_caught(self):
        """조작 수치는 헤징 없이 쓰이면 하드게이트에 걸린다 — 이 시스템의 존재 이유."""
        code, out = run("## S5. 성과\n실제 총 참여자는 243명으로 집계됐습니다.\n")
        self.assertEqual(code, 1)
        self.assertIn("243명", out)
        self.assertIn("하드게이트 실패", out)

    def test_sourced_number_passes(self):
        """원자료에 있는 수치는 통과한다 (전부 막는 게이트는 무용지물)."""
        code, out = run("## S5. 성과\n목표 참여자는 100명이었고 사전 신청자는 18명입니다.\n")
        self.assertEqual(code, 0, out)

    def test_hedged_number_passes(self):
        """헤징 표기된 미확인 수치는 통과시킨다 (단정하지 않았으므로)."""
        code, out = run("## S5. 성과\n참여자는 243명입니다 [확인 필요].\n")
        self.assertEqual(code, 0, out)

    def test_hedge_is_sentence_scoped(self):
        """한 문장의 헤징이 같은 줄 다른 문장의 수치까지 면죄하지 못한다."""
        draft = ("## S5. 성과\n총 참여자는 243명입니다. "
                 "아이디어는 149건 제출됐습니다 [확인 필요 — 보고서와 불일치].\n")
        code, out = run(draft)
        self.assertEqual(code, 1)
        self.assertIn("243명", out)
        self.assertNotIn("149건", out.split("[하드게이트")[0].replace("243명", ""))

    def test_self_declared_confirmation_is_not_evidence(self):
        """초안이 스스로 '✅ 확인'이라 적어도 근거로 인정하지 않는다 (순환논리 차단)."""
        draft = ("## 확인 필요사항\n"
                 "| 총 참여자 수 | ✅ 확인 — 243명 (사전 126명 + 현장 117명) |\n")
        code, out = run(draft)
        self.assertEqual(code, 1)
        self.assertIn("243명", out)

    def test_arithmetic_consistency_is_not_evidence(self):
        """파생 비율이 산술적으로 맞아떨어져도 원본 수치의 근거가 되지 않는다."""
        draft = "## S5. 성과\n243명 중 126명이 사전 신청자로 51.9%를 차지했습니다.\n"
        code, out = run(draft)
        self.assertEqual(code, 1)
        for token in ("243명", "126명", "51.9%"):
            self.assertIn(token, out)

    def test_missing_source_blocks_pass(self):
        """원자료가 없으면 통과(0)도 실패(1)도 아닌 '대조 불가'(2)로 중단한다."""
        with tempfile.TemporaryDirectory() as d:
            draft = os.path.join(d, "nosrc-2026-blog-draft.md")
            with open(draft, "w", encoding="utf-8") as f:
                f.write("## S5\n243명이 참여했습니다.\n")
            p = subprocess.run([sys.executable, AUDIT, draft],
                               capture_output=True, text=True, cwd=d)
            self.assertEqual(p.returncode, 2)
            self.assertIn("대조 불가", p.stdout)

    def test_dates_compared_as_whole_dates(self):
        """날짜는 파편(30일)이 아니라 날짜 전체로 대조한다. 표기 형식이 달라도 인정."""
        code, out = run("## S1\n2026년 4월 27일에 열렸습니다.\n")
        self.assertEqual(code, 0, out)

    def test_wrong_date_is_caught(self):
        code, out = run("## S1\n2026년 5월 27일에 열렸습니다.\n")
        self.assertEqual(code, 1, out)

    def test_meta_sections_excluded(self):
        """자체 채점표·태그 개수는 사실 주장이 아니므로 대조 대상이 아니다."""
        draft = ("## S5. 성과\n목표 100명이었습니다.\n"
                 "## 자체 퇴고 결과\n| SEO | 27/30 | 롱테일 4개, 태그 9개 |\n"
                 "## 태그\n태그 9개 입력\n")
        code, out = run(draft)
        self.assertEqual(code, 0, out)

    def test_unit_mismatch_not_counted_as_confirmed(self):
        """숫자만 같고 단위가 다르면 '확인'으로 인정하지 않는다 (18명 ↔ 18개)."""
        code, out = run("## S3\n부스는 18개였습니다.\n")
        self.assertEqual(code, 1, out)
        self.assertIn("불일치", out)


class TestSourceDiscovery(unittest.TestCase):
    """원자료 자동탐색은 실행 위치(cwd)에 좌우되면 안 된다."""

    DRAFT = "## S5. 성과\n목표 참여자는 100명이었고 사전 신청자는 18명입니다.\n"

    def test_finds_sources_from_unrelated_cwd(self):
        """프로젝트 루트가 아닌 cwd에서 실행해도 원자료를 찾아 대조한다."""
        code, out = run_auto(self.DRAFT, primary=SOURCE, cwd=tempfile.gettempdir())
        self.assertEqual(code, 0, out)
        self.assertIn("x-2026-source.md", out)

    def test_same_verdict_from_root_cwd(self):
        """cwd가 `/`여도 결과가 같다 — 경로 계산이 실행 위치를 타지 않는다."""
        code, out = run_auto(self.DRAFT, primary=SOURCE, cwd=os.sep)
        self.assertEqual(code, 0, out)

    def test_cwd_does_not_hide_fabrication(self):
        """다른 cwd라서 원자료를 못 찾아 '대조 불가'로 새는 일이 없어야 한다."""
        code, out = run_auto("## S5\n총 참여자는 243명입니다.\n",
                             primary=SOURCE, cwd=tempfile.gettempdir())
        self.assertEqual(code, 1, out)
        self.assertIn("243명", out)


class TestPrimarySourcePriority(unittest.TestCase):
    """블로그는 archive_draft의 파생본이다. 파생본만으로 정량 수치를 통과시키면
    아카이브의 오기가 그대로 발행된다 (순환 검증)."""

    def test_derived_only_quantity_is_blocked(self):
        """정량 수치의 근거가 archive_draft에만 있으면 '대조 불가'(2)로 막는다."""
        code, out = run_auto("## S5\n총 참여자는 243명입니다.\n",
                             primary="# 원본\n- 목표 참여자 100명\n", derived=ARCHIVE)
        self.assertEqual(code, 2, out)
        self.assertIn("243명", out)
        self.assertIn("대조 불가", out)

    def test_no_primary_source_blocks_quantity(self):
        """fact_sources가 아예 없으면 archive_draft가 있어도 정량 수치는 통과 불가."""
        code, out = run_auto("## S5\n총 참여자는 243명입니다.\n", derived=ARCHIVE)
        self.assertEqual(code, 2, out)
        self.assertIn("사용자 제공 원본", out)

    def test_structural_number_may_rely_on_derived(self):
        """존 개수 같은 구조 서술은 파생본 근거로도 확인을 인정한다."""
        code, out = run_auto("## S3\n6개 존을 동시에 운영했습니다.\n",
                             primary="# 원본\n- 목표 참여자 100명\n", derived=ARCHIVE)
        self.assertEqual(code, 0, out)

    def test_primary_source_confirms_quantity(self):
        """사용자 원본에 있는 정량 수치는 정상 통과한다 (과잉 차단 방지)."""
        code, out = run_auto("## S5\n총 참여자는 243명입니다.\n",
                             primary="# 원본\n- 총 실제 참여자: 243명\n", derived=ARCHIVE)
        self.assertEqual(code, 0, out)

    def test_explicit_source_flag_is_treated_as_primary(self):
        """사람이 --source로 지목한 경로는 원본으로 본다 (기존 호출 방식 유지)."""
        code, out = run("## S5. 성과\n목표 참여자는 100명입니다.\n")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
