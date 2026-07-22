from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, ClassVar

sys.dont_write_bytecode = True

REPO_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_DIR / "skills" / "pishi-normalno"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import audit_russian_text as audit  # type: ignore[import-not-found]
from audit_russian_text import Finding


class AuditRussianTextTests(unittest.TestCase):
    config: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = audit.load_config(SKILL_DIR / "references" / "patterns.json")

    def audit(self, text: str, **kwargs: Any) -> list[Finding]:
        parameters: dict[str, Any] = {
            "genre": "neutral",
            "config": self.config,
        }
        parameters.update(kwargs)
        return audit.audit_text(text, **parameters)  # type: ignore[no-any-return]

    @staticmethod
    def codes(findings: list[Finding]) -> set[str]:
        return {finding.code for finding in findings}

    def test_long_dash_is_an_error(self) -> None:
        text = "Факт " + chr(0x2014) + " пояснение."
        findings = self.audit(text)
        self.assertIn("unicode-long-dash", self.codes(findings))
        item = next(finding for finding in findings if finding.code == "unicode-long-dash")
        self.assertEqual(item.severity, "error")

    def test_dotted_letters_are_errors(self) -> None:
        text = chr(0x0401) + "лка и вс" + chr(0x0451) + " готово."
        findings = self.audit(text)
        matches = [finding for finding in findings if finding.code == "unicode-dotted-letter"]
        self.assertEqual(len(matches), 2)

    def test_arrow_and_emoji_are_errors(self) -> None:
        text = "Шаг 1 " + chr(0x2192) + " шаг 2 " + chr(0x1F680)
        findings = self.audit(text)
        self.assertIn("unicode-arrow", self.codes(findings))
        self.assertIn("unicode-decorative", self.codes(findings))

    def test_protected_code_is_ignored_by_default(self) -> None:
        text = "Код: `" + chr(0x2014) + "`."
        self.assertNotIn("unicode-long-dash", self.codes(self.audit(text)))
        findings = self.audit(text, include_protected=True)
        self.assertIn("unicode-long-dash", self.codes(findings))

    def test_html_entity_is_an_error(self) -> None:
        findings = self.audit("Факт &mdash; пояснение.")
        self.assertIn("unicode-dash-entity", self.codes(findings))

    def test_service_leak_is_an_error(self) -> None:
        findings = self.audit("Источник: turn12search4.")
        self.assertIn("service-leak", self.codes(findings))

    def test_empty_opening_is_detected(self) -> None:
        findings = self.audit("В современном мире сервисы постоянно меняются.")
        self.assertIn("empty-modernity-opening", self.codes(findings))

    def test_legal_profile_allows_bureaucratic_predicate(self) -> None:
        text = "Комиссия осуществляет проведение проверки в установленный срок."
        findings = self.audit(text, genre="legal")
        self.assertNotIn("bureaucratic-predicate", self.codes(findings))

    def test_legal_profile_allows_integral_part_formula(self) -> None:
        text = "Настоящее условие является неотъемлемой частью Договора."
        findings = self.audit(text, genre="legal")
        self.assertNotIn("integral-part-cliche", self.codes(findings))
        self.assertNotIn("importance-inflation", self.codes(findings))

    def test_neutral_profile_marks_integral_part_formula(self) -> None:
        text = "Дизайн является неотъемлемой частью успешного продукта."
        findings = self.audit(text)
        self.assertIn("integral-part-cliche", self.codes(findings))

    def test_neutral_profile_marks_bureaucratic_predicate(self) -> None:
        text = "Команда осуществляет проведение проверки каждую пятницу."
        findings = self.audit(text)
        self.assertIn("bureaucratic-predicate", self.codes(findings))

    def test_clean_concrete_text_has_no_findings(self) -> None:
        text = (
            "Вчера команда обновила форму оплаты. "
            "Теперь покупатель видит комиссию до подтверждения заказа."
        )
        self.assertEqual(self.audit(text), [])

    def test_duplicate_sentence_is_detected(self) -> None:
        sentence = "Команда проверила форму оплаты и исправила ошибку в итоговой сумме."
        findings = self.audit(sentence + " " + sentence)
        self.assertIn("duplicate-sentence", self.codes(findings))

    def test_repeated_sentence_start_is_informational(self) -> None:
        text = " ".join(
            (
                "Команда проверила форму.",
                "Команда проверила письмо.",
                "Команда проверила отчет.",
                "Клиент получил ответ.",
                "Оплата прошла успешно.",
            )
        )
        findings = self.audit(text)
        item = next(finding for finding in findings if finding.code == "repeated-sentence-start")
        self.assertEqual(item.severity, "info")

    def test_source_comparison_detects_changed_number(self) -> None:
        findings = self.audit("Срок составляет 12 дней.", source_text="Срок составляет 10 дней.")
        codes = self.codes(findings)
        self.assertIn("source-number-missing", codes)
        self.assertIn("source-number-added", codes)

    def test_source_comparison_detects_changed_url(self) -> None:
        source = "Инструкция: https://example.com/old"
        result = "Инструкция: https://example.com/new"
        findings = self.audit(result, source_text=source)
        codes = self.codes(findings)
        self.assertIn("source-url-missing", codes)
        self.assertIn("source-url-added", codes)

    def test_source_comparison_marks_modality_as_warning(self) -> None:
        findings = self.audit("Оплата доступна.", source_text="Оплата доступна, если счет активен.")
        item = next(finding for finding in findings if finding.code == "source-modality-missing")
        self.assertEqual(item.severity, "warning")

    def test_specific_final_question_does_not_add_claim_modality(self) -> None:
        source = "А вы? Кто уже так делал?"
        result = (
            "Если уже надиктовываешь промпты, что голосом получается "
            "сформулировать лучше, чем с клавиатуры?"
        )
        findings = self.audit(result, source_text=source, genre="social")
        self.assertNotIn("source-modality-added", self.codes(findings))

    def test_added_statement_condition_still_warns(self) -> None:
        source = "Оплата доступна."
        result = "Оплата доступна, если счет активен."
        findings = self.audit(result, source_text=source)
        self.assertIn("source-modality-added", self.codes(findings))

    def test_source_comparison_detects_added_prescription(self) -> None:
        source = "Иногда текст надо сократить."
        result = "Иногда текст надо сократить. Поэтому сокращать надо повторы."
        findings = self.audit(result, source_text=source)
        self.assertIn("source-modality-added", self.codes(findings))

    def test_line_and_column_are_reported(self) -> None:
        text = "Первая строка.\nВторая " + chr(0x2014) + " строка."
        findings = self.audit(text)
        item = next(finding for finding in findings if finding.code == "unicode-long-dash")
        self.assertEqual(item.line, 2)
        self.assertEqual(item.column, 8)

    def test_json_payload_is_serializable(self) -> None:
        findings = self.audit("Источник: turn1search2.")
        payload = {"findings": [finding.to_dict() for finding in findings]}
        rendered = json.dumps(payload, ensure_ascii=False)
        self.assertIn("service-leak", rendered)

    def test_exit_status_respects_strict_mode(self) -> None:
        warning = audit.Finding(
            severity="warning",
            code="sample",
            category="sample",
            message="sample",
            line=1,
            column=1,
            excerpt="sample",
            suggestion="sample",
            confidence="medium",
        )
        self.assertEqual(audit.exit_status([warning], strict=False), 0)
        self.assertEqual(audit.exit_status([warning], strict=True), 1)

    def test_social_profile_accepts_clean_post(self) -> None:
        text = "Вчера надиктовал промпт голосом. Мысль сложилась за один проход."
        self.assertEqual(self.audit(text, genre="social"), [])

    def test_mixed_address_register_is_detected(self) -> None:
        text = "Трата твоего времени. А вы уже так делали?"
        findings = self.audit(text, genre="social")
        self.assertIn("mixed-address-register", self.codes(findings))

    def test_address_inside_quotation_is_ignored(self) -> None:
        text = "«Ты уже закончил?» спросил редактор. Вы можете прислать файл завтра."
        findings = self.audit(text, genre="social")
        self.assertNotIn("mixed-address-register", self.codes(findings))

    def test_source_comparison_detects_changed_address(self) -> None:
        findings = self.audit(
            "Вам доступен отчет.",
            source_text="Тебе доступен отчет.",
            genre="social",
        )
        self.assertIn("source-address-changed", self.codes(findings))

    def test_generic_engagement_bait_is_informational(self) -> None:
        findings = self.audit(
            "Оставил черновик как есть. А вы?",
            genre="social",
        )
        item = next(finding for finding in findings if finding.code == "generic-engagement-bait")
        self.assertEqual(item.severity, "info")

    def test_generic_so_have_you_question_is_detected(self) -> None:
        findings = self.audit("Поймал тот же паттерн. Ты уже так делал?", genre="social")
        self.assertIn("generic-engagement-bait", self.codes(findings))

    def test_specific_experience_question_is_not_generic_bait(self) -> None:
        text = "Кто уже надиктовывал промпт голосом и что получилось?"
        findings = self.audit(text, genre="social")
        self.assertNotIn("generic-engagement-bait", self.codes(findings))

    def test_urgency_claim_requires_review(self) -> None:
        findings = self.audit("Только сегодня доступен тариф.", genre="marketing")
        item = next(finding for finding in findings if finding.code == "urgency-claim")
        self.assertEqual(item.severity, "warning")

    def test_question_rewrite_residue_is_detected(self) -> None:
        text = "Если уже надиктовываешь промпты, что так получается сформулировать?"
        findings = self.audit(text, genre="social")
        item = next(finding for finding in findings if finding.code == "question-rewrite-residue")
        self.assertEqual(item.severity, "warning")

    def test_inanimate_subject_spending_time_is_detected(self) -> None:
        findings = self.audit("Аккуратный промпт тратит твое время.", genre="social")
        item = next(finding for finding in findings if finding.code == "inanimate-spends-time")
        self.assertEqual(item.severity, "warning")

    def test_natural_time_collocation_is_not_flagged(self) -> None:
        findings = self.audit("Аккуратный промпт отнимает у тебя время.", genre="social")
        self.assertNotIn("inanimate-spends-time", self.codes(findings))

    def test_nominal_fragment_pair_is_detected(self) -> None:
        text = "Аккуратный промпт. Трата твоего времени."
        findings = self.audit(text, genre="social")
        item = next(finding for finding in findings if finding.code == "nominal-fragment-pair")
        self.assertEqual(item.severity, "warning")

    def test_source_comparison_detects_added_relation_split(self) -> None:
        source = "Аккуратный промпт " + chr(0x2014) + " трата твоего времени."
        result = "Аккуратный промпт. Трата твоего времени."
        findings = self.audit(result, source_text=source, genre="social")
        self.assertIn("source-relation-split", self.codes(findings))

    def test_connected_hook_has_no_fragment_warning(self) -> None:
        text = "Аккуратный промпт отнимает у тебя время."
        findings = self.audit(text, genre="social")
        self.assertNotIn("nominal-fragment-pair", self.codes(findings))

    def test_short_complete_sentences_are_not_fragment_pair(self) -> None:
        for text in (
            "Не получилось. Попробую завтра.",
            "Обидно. Завтра попробую снова.",
            "Готово. Файл сохранен.",
        ):
            with self.subTest(text=text):
                findings = self.audit(text, genre="social")
                self.assertNotIn("nominal-fragment-pair", self.codes(findings))

    def test_literary_nominal_pair_is_only_informational(self) -> None:
        findings = self.audit("Ночь. Пустая улица.", genre="editorial")
        item = next(finding for finding in findings if finding.code == "nominal-fragment-pair")
        self.assertEqual(item.severity, "info")

    def test_short_abstract_run_is_detected(self) -> None:
        findings = self.audit("Скорость. Контроль. Результат.", genre="social")
        self.assertIn("short-abstract-run", self.codes(findings))

    def test_headings_and_lists_are_not_fragment_pairs(self) -> None:
        text = "# Скорость\n\n- Контроль\n- Результат"
        findings = self.audit(text, genre="social")
        self.assertNotIn("nominal-fragment-pair", self.codes(findings))
        self.assertNotIn("short-abstract-run", self.codes(findings))

    def test_spaced_ascii_hyphen_is_allowed(self) -> None:
        text = "Отчет " + "-" + " это снимок расходов."
        findings = self.audit(text)
        self.assertNotIn("ascii-punctuation-dash", self.codes(findings))

    def test_word_hyphen_and_list_marker_are_allowed(self) -> None:
        text = "Санкт-Петербург\n\n- первый пункт\n- второй пункт"
        findings = self.audit(text)
        self.assertNotIn("ascii-punctuation-dash", self.codes(findings))

    def test_ascii_arrow_is_an_error_outside_code(self) -> None:
        arrow = "-" + ">"
        findings = self.audit("Черновик " + arrow + " публикация.")
        self.assertIn("ascii-arrow", self.codes(findings))
        protected = self.audit("`черновик " + arrow + " публикация`")
        self.assertNotIn("ascii-arrow", self.codes(protected))

    def test_service_leak_inside_code_is_ignored(self) -> None:
        findings = self.audit("Пример: `turn12search4`.")
        self.assertNotIn("service-leak", self.codes(findings))

    def test_mixed_script_word_is_an_error(self) -> None:
        text = "к" + "o" + "д"
        findings = self.audit(text)
        item = next(finding for finding in findings if finding.code == "mixed-script-word")
        self.assertEqual(item.severity, "error")

    def test_extended_service_leaks_are_detected(self) -> None:
        for text in (
            "Источник citeturn4search2.",
            "Файл turn8file3.",
            "Остаток <think>.",
        ):
            with self.subTest(text=text):
                self.assertIn("service-leak", self.codes(self.audit(text)))

    def test_final_question_chain_is_detected(self) -> None:
        text = "Попробую голосовой ввод. А вы? Кто уже так делал?"
        findings = self.audit(text, genre="social")
        item = next(finding for finding in findings if finding.code == "final-question-chain")
        self.assertEqual(item.severity, "warning")

    def test_final_question_chain_can_mention_interview(self) -> None:
        text = "Кто вел интервью с моделью? Что получилось?"
        findings = self.audit(text, genre="social")
        self.assertIn("final-question-chain", self.codes(findings))

    def test_interview_heading_allows_multiple_questions(self) -> None:
        text = "Интервью:\nЧто вы сделали?\nЧто получилось?"
        findings = self.audit(text, genre="social")
        self.assertNotIn("final-question-chain", self.codes(findings))

    def test_questions_across_lines_in_final_paragraph_are_detected(self) -> None:
        text = "Попробую.\n\nА вы уже пробовали?\nЧто получилось?"
        findings = self.audit(text, genre="social")
        self.assertIn("final-question-chain", self.codes(findings))

    def test_single_specific_question_is_not_a_chain(self) -> None:
        text = "Что голосом получилось сформулировать лучше, чем с клавиатуры?"
        findings = self.audit(text, genre="social")
        self.assertNotIn("final-question-chain", self.codes(findings))

    def test_source_comparison_detects_added_benefit_claim(self) -> None:
        source = "Сервис выгружает диалоги в CSV."
        result = "Сервис выгружает диалоги в CSV и экономит время."
        findings = self.audit(result, source_text=source, genre="marketing")
        self.assertIn("source-benefit-claim-added", self.codes(findings))

    def test_existing_benefit_claim_is_not_marked_as_added(self) -> None:
        text = "Сервис экономит время."
        findings = self.audit(text, source_text=text, genre="marketing")
        self.assertNotIn("source-benefit-claim-added", self.codes(findings))

    def test_source_comparison_detects_added_causality(self) -> None:
        source = "Форму сократили. Конверсия выросла."
        result = "Форму сократили, поэтому конверсия выросла."
        findings = self.audit(result, source_text=source, genre="marketing")
        self.assertIn("source-causality-added", self.codes(findings))

    def test_source_comparison_detects_split_paired_relation(self) -> None:
        source = "На входе каша, на выходе мысль яснее."
        result = "На входе каша. На выходе мысль яснее."
        findings = self.audit(result, source_text=source, genre="social")
        self.assertIn("source-paired-relation-split", self.codes(findings))

    def test_intact_paired_relation_has_no_split_warning(self) -> None:
        text = "На входе каша, а на выходе мысль яснее."
        findings = self.audit(text, source_text=text, genre="social")
        self.assertNotIn("source-paired-relation-split", self.codes(findings))

    def test_source_comparison_detects_mechanical_dash_replacement(self) -> None:
        source = "Аккуратный промпт " + chr(0x2014) + " трата времени."
        result = "Аккуратный промпт " + "-" + " трата времени."
        findings = self.audit(result, source_text=source, genre="social")
        self.assertIn("source-mechanical-dash-replacement", self.codes(findings))

    def test_predicative_dash_rewrite_has_no_mechanical_warning(self) -> None:
        source = "Аккуратный промпт " + chr(0x2014) + " трата времени."
        result = "Аккуратный промпт отнимает время."
        findings = self.audit(result, source_text=source, genre="social")
        self.assertNotIn("source-mechanical-dash-replacement", self.codes(findings))

    def test_agent_metadata_allows_implicit_invocation(self) -> None:
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: true", metadata)
        self.assertIn('icon_small: "./assets/mark.svg"', metadata)
        self.assertTrue((SKILL_DIR / "assets" / "mark.svg").is_file())

    def test_skill_trigger_covers_creation_editing_and_embedded_use(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill_text.split("---", 2)[1].lower()
        description = frontmatter.split("description:", 1)[1].strip()
        self.assertLessEqual(len(description), 200)
        for phrase in (
            "пишет",
            "редактирует",
            "посты",
            "smm",
            "маркетинг",
            "финальный embedded-проход",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, frontmatter)

    def test_skill_trigger_declares_near_miss_exclusions(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        body = skill_text.split("---", 2)[2].lower()
        for phrase in (
            "кода",
            "команд",
            "логов",
            "дословных цитат",
            "коротких фактических ответов",
            "только к пользовательской прозе",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_agent_contract_routes_to_skill_and_auditor(self) -> None:
        template = REPO_DIR / "templates" / "AGENTS.md"
        instructions = template.read_text(encoding="utf-8")
        for phrase in (
            "Автоматический вызов `pishi-normalno`",
            "$pishi-normalno",
            "audit_russian_text.py",
            "коротких фактических ответов",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, instructions)

    def test_configured_regular_expressions_compile(self) -> None:
        audit.validate_config(self.config)

    def test_skill_files_have_no_forbidden_literal_codepoints(self) -> None:
        allowed_suffixes = {".md", ".py", ".json", ".yaml", ".yml"}
        forbidden: list[tuple[Path, int, int]] = []
        for path in SKILL_DIR.rglob("*"):
            if not path.is_file() or path.suffix not in allowed_suffixes:
                continue
            text = path.read_text(encoding="utf-8")
            for index, char in enumerate(text):
                codepoint = ord(char)
                if codepoint in {0x2013, 0x2014, 0x0451, 0x0401}:
                    forbidden.append((path, index, codepoint))
                if audit._in_ranges(codepoint, audit.ARROW_RANGES):
                    forbidden.append((path, index, codepoint))
        self.assertEqual(forbidden, [])


if __name__ == "__main__":
    unittest.main()
