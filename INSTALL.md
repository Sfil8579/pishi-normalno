# Установка без путаницы

Ниже пять отдельных инструкций. Выберите программу, которой реально пользуетесь, и выполните только ее раздел.

Проверено 22 июля 2026 года.

| Где вы пишете | Что устанавливать | Сколько действий |
|---|---|---|
| Claude в браузере | ZIP через `Customize > Skills` | Скачать и загрузить |
| Claude Desktop | Тот же ZIP через `Customize > Skills` | Скачать и загрузить |
| Claude Code в терминале | Папку в `~/.claude/skills` | Одна команда |
| ChatGPT | ZIP в Workspace Agent или один MD в обычный Project | Скачать и загрузить |
| Codex app, CLI или IDE | Папку в `~/.agents/skills` | Одна команда |

## Claude в браузере

Подходит для Free, Pro, Max, Team и Enterprise. В аккаунте должно быть включено выполнение кода.

1. [Скачайте `pishi-normalno.zip`](https://github.com/fsbtactic-code/pishi-normalno/releases/download/v1.0.0/pishi-normalno.zip).
2. Откройте Claude.
3. Откройте `Settings > Capabilities`.
4. Включите `Code execution and file creation`.
5. Откройте `Customize > Skills`.
6. Нажмите `+`, затем `Create skill` и `Upload a skill`.
7. Выберите скачанный `pishi-normalno.zip`.
8. Убедитесь, что переключатель скилла включен.

Готово. Команду с названием скилла писать не нужно. Попросите Claude написать пост, письмо или текст лендинга обычными словами.

Если раздела `Skills` нет, сначала проверьте `Code execution and file creation`. В рабочем аккаунте Team или Enterprise функция также может быть отключена администратором.

Официальная инструкция: [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

## Claude Desktop

Используйте тот же способ, что и в браузере:

1. [Скачайте `pishi-normalno.zip`](https://github.com/fsbtactic-code/pishi-normalno/releases/download/v1.0.0/pishi-normalno.zip).
2. Откройте Claude Desktop.
3. Откройте `Customize > Skills`.
4. Нажмите `+`, затем `Create skill` и `Upload a skill`.
5. Выберите ZIP и включите скилл.

Локальную папку искать не нужно. Загруженный скилл хранится в вашем аккаунте Claude и доступен в обычном Chat и Cowork. Для Team и Enterprise администратор может загрузить его сразу всей организации.

## Claude Code

Это вариант для программы `claude`, которую запускают в терминале.

### Windows

Откройте PowerShell, вставьте всю строку и нажмите Enter:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.ps1))) -Target claude
```

### macOS или Linux

Откройте Terminal, вставьте строку и нажмите Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.sh | bash -s -- --target claude
```

Скилл окажется здесь:

- Windows: `$HOME\.claude\skills\pishi-normalno\SKILL.md`
- macOS и Linux: `~/.claude/skills/pishi-normalno/SKILL.md`

Проверка на Windows:

```powershell
Test-Path "$HOME\.claude\skills\pishi-normalno\SKILL.md"
```

Проверка на macOS и Linux:

```bash
test -f ~/.claude/skills/pishi-normalno/SKILL.md && echo "Готово"
```

Если получили `True` или `Готово`, откройте новый сеанс Claude Code. Скилл вызывается автоматически по описанию задачи. Его также можно вызвать вручную командой `/pishi-normalno`.

Официальная документация: [Extend Claude with skills](https://code.claude.com/docs/en/skills).

## ChatGPT

В ChatGPT есть два разных варианта. Сначала посмотрите, есть ли у вас раздел `Agents`.

### Вариант A. Есть Workspace Agents

Полная загрузка Agent Skill сейчас доступна в research preview для ChatGPT Business, Enterprise и Edu.

1. [Скачайте `pishi-normalno.zip`](https://github.com/fsbtactic-code/pishi-normalno/releases/download/v1.0.0/pishi-normalno.zip).
2. Откройте `Agents` в ChatGPT.
3. Создайте нового агента или откройте существующего.
4. Нажмите `Add skill`.
5. Выберите скачанный ZIP.
6. Сохраните агента и откройте `Try in ChatGPT`.

Внутри этого агента скилл будет подключаться по смыслу запроса. Официальный пример: [Building workspace agents in ChatGPT](https://developers.openai.com/cookbook/articles/chatgpt-agents-sales-meeting-prep#3-enabling-skills-and-memories-for-consistent-customized-outputs).

### Вариант B. Обычный ChatGPT без Agents

В обычном аккаунте нельзя честно установить полный локальный Agent Skill на все чаты. Рабочий fallback действует внутри одного Project:

1. [Скачайте `pishi-normalno-chatgpt.md`](https://github.com/fsbtactic-code/pishi-normalno/releases/download/v1.0.0/pishi-normalno-chatgpt.md).
2. Создайте новый Project в ChatGPT.
3. Добавьте скачанный файл в файлы проекта.
4. Добавьте в инструкции проекта одну строку:

```text
Автоматически применяй правила из pishi-normalno-chatgpt.md ко всем существенным русским текстам в этом проекте, если они не противоречат моему запросу.
```

5. Пишите в чат внутри этого Project.

Этот вариант сохраняет полную редакторскую базу, но не запускает локальный Python-аудитор и не действует вне проекта.

### ChatGPT Desktop с режимом Codex

Если в приложении выбран именно Codex, используйте установку из следующего раздела. После нее скилл появится в боковом разделе `Skills` и сможет подключаться автоматически.

## Codex app, Codex CLI и IDE

Одна глобальная установка работает для локального Codex app, CLI и расширения IDE.

### Windows

Откройте PowerShell, вставьте строку и нажмите Enter:

```powershell
irm https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.ps1 | iex
```

### macOS или Linux

Откройте Terminal, вставьте строку и нажмите Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.sh | bash
```

Скилл окажется здесь:

- Windows: `$HOME\.agents\skills\pishi-normalno\SKILL.md`
- macOS и Linux: `~/.agents/skills/pishi-normalno/SKILL.md`

Проверка на Windows:

```powershell
Test-Path "$HOME\.agents\skills\pishi-normalno\SKILL.md"
```

Проверка на macOS и Linux:

```bash
test -f ~/.agents/skills/pishi-normalno/SKILL.md && echo "Готово"
```

Если получили `True` или `Готово`, перезапустите Codex, если скилл не появился сразу. Откройте `Skills` и найдите `Пиши нормально`.

Пользователю не нужно писать `$pishi-normalno` перед каждым запросом. В metadata включен автоматический вызов, а описание перечисляет посты, маркетинг, SMM, письма, статьи, лендинги, CTA и другие подходящие задачи.

Официальная документация: [Build skills](https://learn.chatgpt.com/docs/build-skills).

## Обновление

### Codex на Windows

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.ps1))) -Target codex -Update
```

### Claude Code на Windows

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.ps1))) -Target claude -Update
```

### Codex на macOS или Linux

```bash
curl -fsSL https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.sh | bash -s -- --target codex --update
```

### Claude Code на macOS или Linux

```bash
curl -fsSL https://raw.githubusercontent.com/fsbtactic-code/pishi-normalno/v1.0.0/install.sh | bash -s -- --target claude --update
```

Инсталлятор сначала проверяет SHA256. При обновлении он сохраняет предыдущую установку в резервной папке.

Для Claude, Claude Desktop и ChatGPT обновление выполняется повторной загрузкой нового файла из свежего релиза.

## Установка только в один репозиторий

Если скилл нужен не везде, а только в одном проекте, скопируйте папку `skills/pishi-normalno`:

- для Codex в `<ваш-репозиторий>/.agents/skills/pishi-normalno`;
- для Claude Code в `<ваш-репозиторий>/.claude/skills/pishi-normalno`.

Внутри целевой папки должен находиться файл `SKILL.md`.
