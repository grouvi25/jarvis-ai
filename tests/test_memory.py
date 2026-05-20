"""Тесты памяти J.A.R.V.I.S."""

import tempfile
from pathlib import Path

from jarvis.core.memory import Memory


class TestMemory:
    """Тесты сохранения истории и контактов."""

    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.memory = Memory(data_dir=self.tmp_dir)

    def test_save_and_load_history(self) -> None:
        messages = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте, сэр"},
        ]
        self.memory.save_history(messages)
        loaded = self.memory.get_history()
        assert len(loaded) == 2
        assert loaded[0]["content"] == "Привет"

    def test_clear_history(self) -> None:
        self.memory.save_history([{"role": "user", "content": "Тест"}])
        self.memory.clear_history()
        assert self.memory.get_history() == []

    def test_add_contact(self) -> None:
        self.memory.add_contact("Маша", "@masha", "девушка")
        contact = self.memory.get_contact("маша")
        assert contact is not None
        assert contact["telegram_id"] == "@masha"
        assert contact["label"] == "девушка"

    def test_find_by_label(self) -> None:
        self.memory.add_contact("Маша", "@masha", "девушка")
        contact = self.memory.get_contact("девушка")
        assert contact is not None
        assert contact["name"] == "Маша"

    def test_list_contacts(self) -> None:
        self.memory.add_contact("Маша", "@masha", "девушка")
        self.memory.add_contact("Мама", "@mama", "мама")
        contacts = self.memory.list_contacts()
        assert len(contacts) == 2

    def test_remove_contact(self) -> None:
        self.memory.add_contact("Маша", "@masha")
        assert self.memory.remove_contact("маша")
        assert self.memory.get_contact("маша") is None

    def test_contact_not_found(self) -> None:
        assert self.memory.get_contact("несуществующий") is None
