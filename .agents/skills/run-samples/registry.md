# Section Registry

Each entry: section path, type (`cli`/`docker`/`special`), and the command to run from within the section directory.

## Chapter 2

| Section | Type | Command |
|---------|------|---------|
| chapter_2/section_1 | cli | `uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH` |
| chapter_2/section_2 | cli | `uv run python -m src.main -m GPT_5_4_MINI -e example_1_simple_user_model` |
| chapter_2/section_3 | cli | `uv run python -m src.main -m GEMINI_2_5_FLASH -i data/002_請求書_47491048.png` |
| chapter_2/section_4 | cli | `uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH` |
| chapter_2/section_5 | cli | `uv run python -m src.main -m GEMINI_2_5_FLASH` |
| chapter_2/section_6 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8001/batch/queue/stats && make docker-down` |
| chapter_2/section_7 | special | `uv run python run_server.py & sleep 5 && uv run python example_client.py --prompt 'こんにちは'; kill %1 2>/dev/null` |
| chapter_2/section_8 | cli | `uv run python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH` |
| chapter_2/section_9 | cli | `uv run python -m src.main -m GPT_5_4 -t templates/character_generation.yaml` |
| chapter_2/section_10 | cli | `uv run python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH` |
| chapter_2/section_11 | cli | `uv run python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH -p` |
| chapter_2/section_12 | cli | `uv run python -m src.main -m GPT_5_4 -t templates/character_generation.yaml` |
| chapter_2/section_13 | cli | `uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -lat 35.6762 -lon 139.6503` |
| chapter_2/section_14 | cli | `uv run python -m src.main -m claude-sonnet-4-6 -i data/contract_0.md` |

## Chapter 3

| Section | Type | Command |
|---------|------|---------|
| chapter_3/section_1 | cli | `uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH` |
| chapter_3/section_2 | cli | `uv run python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH -am GPT_5_4_MINI` |
| chapter_3/section_3 | cli | `uv run python -m src.main -rf character_requests.yaml -m GEMINI_2_5_FLASH -p 2` |
| chapter_3/section_4 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8000/health && make docker-down` |
| chapter_3/section_5 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8000/health && make docker-down` |
| chapter_3/section_6 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8080/health && make docker-down` |

## Chapter 4

| Section | Type | Command |
|---------|------|---------|
| chapter_4/section_1 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8000/health && make docker-down` |
| chapter_4/section_2 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8000/health && make docker-down` |
| chapter_4/section_3 | docker | `make docker-build && make docker-up && sleep 10 && curl -s http://localhost:8000/health && make docker-down` |
| chapter_4/section_4 | cli | `uv run python -m src.main query -q 'What is structured output?'` |
| chapter_4/section_5 | cli | `uv run python -m src.main -lp GEMINI -m GEMINI_2_5_FLASH -dp dataset/document_0.md` |
| chapter_4/section_6 | cli | `uv run python -m src.main -w example_gemini_simple` |
| chapter_4/section_7 | cli | `uv run python -m src.main -w example_1_manual_di` |
| chapter_4/section_8 | cli | `uv run python -m src.main -a example_1_basic_agent` |
| chapter_4/section_9 | cli | `uv run python -m src.main -a example_1_basic_agent` |

## Chapter 5

| Section | Type | Command |
|---------|------|---------|
| chapter_5/section_1 | cli | `uv run python -m src.main -r '今日は疲れているので簡単な料理がいい'` |
| chapter_5/section_2 | cli | `uv run python -m src.main -r '孤独な宇宙飛行士が地球を見つめながら人生を振り返る物語'` |
| chapter_5/section_3 | cli | `uv run python -m src.main -c example/sample_nda.md -t example/standard_nda_template.md` |
| chapter_5/section_4 | cli | `uv run python -m src.main -g '3ヶ月でPythonプログラミングを習得したい' -h 10` |
| chapter_5/section_5 | cli | `uv run python -m src.main -c data/contract_0.md` |
| chapter_5/section_6 | special | `uv run python -m src.event_runner -w data/ & sleep 15; kill %1 2>/dev/null` |
| chapter_5/section_7 | cli | `uv run python -m src.main generate -g 'Learn Python programming' -h 10 -s beginner` |

## Chapter 6

| Section | Type | Command |
|---------|------|---------|
| chapter_6/section_1 | special | `uv run streamlit run app.py --server.headless true & sleep 10 && curl -s http://localhost:8501 && kill %1 2>/dev/null` |
| chapter_6/section_2 | special | `uv run python -m src.main -lp ANTHROPIC -m CLAUDE_SONNET_4_6` |
| chapter_6/section_3 | cli | `uv run python -m src.main -g FEMALE -a 25 -lp GEMINI -m GEMINI_2_5_FLASH -n 3 -qt 3.0` |
| chapter_6/section_4 | cli | `uv run python -m src.main --theme 'AI in healthcare' --language en -m gemini-2.5-flash` |
| chapter_6/section_5 | cli | `uv run python -m src.main --theme 'AI in healthcare' --language en -m gemini-2.5-flash` |
| chapter_6/section_6 | cli | `uv run python -m src.main --query '全生徒の成績を分析してください'` |
| chapter_6/section_7 | cli | `uv run python -m src.main --query '数学の成績を分析してください'` |
| chapter_6/section_8 | cli | `uv run python -m src.main --agent example_1_agent_with_conservative_lock` |
| chapter_6/section_9 | cli | `uv run python -m src.main --theme 'AI in healthcare' --language en -m gemini-2.5-flash --auto-select` |
