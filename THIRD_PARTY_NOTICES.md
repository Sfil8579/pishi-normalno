# Сторонние материалы и благодарности

## humanizer-ru

При разработке `Пиши нормально` использовали и изучали скилл [`ilyautov/humanizer-ru`](https://github.com/ilyautov/humanizer-ru), включая версию 3.15.1. Отдельные архитектурные компоненты адаптированы из этого проекта, Copyright (c) 2026 Ilya Utov, на условиях MIT License.

Из проекта адаптированы или переосмыслены архитектурные подходы:

- модульное разделение ядра, справочников, сканера и eval;
- несколько независимых редакторских проходов;
- каталог составных русских паттернов;
- optional-морфология и ручной fallback;
- внимание к ложным срабатываниям;
- регрессионная проверка на корпусе примеров.

`Пиши нормально` добавляет source-aware сравнение, карту смысловых связей, защиту предикации, происхождение маркетинговых обещаний, отдельные SMM-профили, написание с нуля и автоматическую маршрутизацию. Проект сознательно не использует detector score, оптимизацию perplexity и burstiness, намеренные ошибки или квоты на языковые украшения.

Основные места адаптации и самостоятельного развития:

- `skills/pishi-normalno/SKILL.md`: прогрессивная загрузка и независимые проходы расширены реестром смысла, голоса, энергии и картой связей;
- `skills/pishi-normalno/references/neural-slop-corpus.md`: составлен отдельный корпус минимальных пар и контрпримеров для русской речи;
- `skills/pishi-normalno/references/research-basis.md`: зафиксированы использованные идеи, источники и границы переноса;
- `skills/pishi-normalno/scripts/audit_russian_text.py`: реализован самостоятельный source-aware аудитор с формальной сверкой исходника и результата;
- `tests/`: добавлены собственные регрессии для семантических связей, маркетинговых обещаний и implicit-вызова.

Проект не связан с Ильей Утовым, не одобрен им и не является официальным продолжением `humanizer-ru`.

Лицензия исходного проекта:

```text
MIT License

Copyright (c) 2026 Ilya Utov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Другие архитектурные ориентиры

- [`hardikpandya/stop-slop`](https://github.com/hardikpandya/stop-slop): компактное ядро и прогрессивная загрузка каталогов.
- [`blader/humanizer`](https://github.com/blader/humanizer): fact lock, режимы редактуры и калибровка по голосу автора.

Ссылки означают исследовательское и архитектурное влияние. Лицензия и авторство каждого стороннего проекта принадлежат его авторам.
