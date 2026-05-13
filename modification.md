# 项目修改说明

本文档记录了为了完成自动化根因分析（RCA）任务而对项目进行的修改以及新增的自动化脚本。

## 1. 依赖项修改

在 `requirements.txt` 文件中添加了以下依赖库，用于支持 DuckDB 数据查询和相关处理：

```text
duckdb>=1.4.2
pyarrow>=12.0.0
sentence-transformers>=2.2.0
```

## 2. 配置文件修改

修改了 `project/taskweaver_config.json` 文件，配置了 LLM（OpenAI）和 Embedding 模型。

主要配置项如下：
- `llm.api_key`: 配置了 OpenAI API Key。
- `llm.model`: 设置为 `gpt-4o-mini`。
- `llm.embedding_model`: 设置为 `text-embedding-ada-002`。

## 3. 自动化脚本

创建了一个名为 `auto_rca_script.py` 的 Python 脚本，用于自动化执行 RCA 分析流程。

该脚本的主要功能包括：
1.  初始化 TaskWeaver 应用。
2.  读取 `question_3/problem.json` 中的任务描述。
3.  将 `question_3/` 目录下的 Parquet 数据文件复制到 TaskWeaver 会话的工作目录。
4.  向 TaskWeaver 发送任务请求，启动分析。
5.  将对话历史和分析结果保存到 `output.json` 文件中。

### 脚本代码 (`auto_rca_script.py`)

```python
import sys
import os
import shutil
import json

# Add current directory to sys.path to ensure taskweaver can be imported
sys.path.insert(0, os.getcwd())

from taskweaver.app.app import TaskWeaverApp

# Configuration
# Use the current project directory
APP_DIR = os.path.join(os.getcwd(), 'project')
DATA_DIR = os.path.join(os.getcwd(), 'question_3')

def main():
    print("Starting Automated RCA Analysis...")

    # 1. Read the task description from problem.json
    problem_file = os.path.join(DATA_DIR, 'problem.json')
    task_description = ""
    try:
        with open(problem_file, 'r') as f:
            content = f.read()
            # Extract the string content from TASK_DESCRIPTION = """..."""
            if 'TASK_DESCRIPTION = """' in content:
                start = content.find('TASK_DESCRIPTION = """') + len('TASK_DESCRIPTION = """')
                end = content.rfind('"""')
                task_description = content[start:end].strip()
            else:
                # Fallback if format is different
                print("Warning: Could not parse TASK_DESCRIPTION from problem.json, using raw content.")
                task_description = content
    except Exception as e:
        print(f"Error reading problem.json: {e}")
        return

    if not task_description:
        print("Error: Empty task description.")
        return

    # 2. Initialize TaskWeaver App
    # Use the configuration from project/taskweaver_config.json
    config_var = {
        "execution_service.kernel_mode": "local",
        "session.max_internal_chat_round_num": 30,
    }

    app = TaskWeaverApp(app_dir=APP_DIR, config=config_var)
    session = app.get_session()
    print(f"Session ID: {session.session_id}")

    # 3. Copy parquet files to the session's cwd
    session_cwd = os.path.join(APP_DIR, "workspace", "sessions", session.session_id, "cwd")
    # Ensure the directory exists (TaskWeaver might create it, but good to be safe)
    if not os.path.exists(session_cwd):
        os.makedirs(session_cwd)

    print(f"Copying data files from {DATA_DIR} to {session_cwd}...")
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".parquet"):
                src = os.path.join(DATA_DIR, filename)
                dst = os.path.join(session_cwd, filename)
                shutil.copy2(src, dst)
                print(f"Copied {filename}")
    else:
        print(f"Error: Data directory {DATA_DIR} does not exist.")
        return

    # 4. Send the task description to TaskWeaver
    print("Sending task to TaskWeaver...")
    try:
        response_round = session.send_message(task_description)

        print(f"Round State: {response_round.state}")
        
        # Save conversation history to output.json
        output_data = []
        for post in response_round.post_list:
            post_dict = {
                "send_from": post.send_from,
                "send_to": post.send_to,
                "message": post.message,
                "attachments": []
            }
            if hasattr(post, 'attachment_list'):
                for attachment in post.attachment_list:
                    att_dict = {}
                    if hasattr(attachment, 'type'):
                        # Handle AttachmentType enum
                        att_type = attachment.type
                        if hasattr(att_type, 'value'):
                            att_dict['type'] = att_type.value
                        else:
                            att_dict['type'] = str(att_type)
                    if hasattr(attachment, 'content'):
                        att_dict['content'] = attachment.content
                    post_dict['attachments'].append(att_dict)
            output_data.append(post_dict)

        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print("Conversation history saved to output.json")

        # 5. Print the result
        print("Analysis finished.")
        for post in response_round.post_list:
            print(f"\nFrom: {post.send_from} -> To: {post.send_to}")
            print(post.message)
            print("-" * 20)
            
            if "Root cause service:" in post.message:
                print("✅ Found Root Cause!")
                
        if response_round.state == "failed":
            print("❌ Round failed!")
            # Check for error messages in posts
            for post in response_round.post_list:
                if post.send_from == "System" or post.send_from == "Planner":
                     print(f"Message from {post.send_from}: {post.message}")

    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        app.stop()

if __name__ == "__main__":
    main()
```

## 4. 运行说明

确保已安装所有依赖项，并在项目根目录下运行以下命令：

```bash
python auto_rca_script.py
```

运行完成后，分析结果和对话历史将保存在 `output.json` 文件中。
