#!/usr/bin/env python3
"""
Notion → GitHub Knowledge Base Sync
双向同步脚本：Notion ↔ GitHub Markdown

工作流：
  1. 从 Notion 提取所有内容（文章 + 数据库条目）
  2. 保存为 Markdown（YAML frontmatter + structured properties）
  3. 维护 page_id ↔ file_path 映射用于双向同步
  4. git commit & push

用法：
  python3 scripts/sync.py              # 默认模式：Notion→GitHub
  python3 scripts/sync.py --reverse     # 方向：GitHub→Notion（更新 Notion）
  python3 scripts/sync.py --dry-run     # 只提取，不 git push
"""

import json
import os
import re
import subprocess
import sys
import hashlib
import time
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
NOTION_KEY_PATH = os.path.expanduser("~/.config/notion/api_key")
NOTION_VERSION = "2025-09-03"
REPO_PATH = os.path.expanduser("~/notion-knowledge-base")
SCRIPTS_DIR = os.path.join(REPO_PATH, "scripts")
MAPPING_FILE = os.path.join(REPO_PATH, "_mapping.json")
STATE_FILE = os.path.join(REPO_PATH, "_sync_state.json")

# Rate limiting: Notion API allows ~3 req/s
API_DELAY = 0.45  # seconds between requests
_last_api_call = 0.0

# Notion Page / Database IDs
MAIN_PAGE_ID = "35666ad7-c9c4-8044-8014-e057aaa752a6"     # 通识分享企划—备份
TOOLS_DB_ID = "abe66ad7-c9c4-82d2-b528-0700be6887d5"      # 工具数据库
COMMUNITY_DB_ID = "73b66ad7-c9c4-82f9-8f1f-879d86a55b75"  # 社区数据库

DRY_RUN = "--dry-run" in sys.argv
REVERSE = "--reverse" in sys.argv

# ── Auth ────────────────────────────────────────────────────────────────────
if not os.path.exists(NOTION_KEY_PATH):
    print("❌ Notion API key not found at", NOTION_KEY_PATH)
    sys.exit(1)

with open(NOTION_KEY_PATH) as f:
    NOTION_KEY = f.read().strip()


# ── Notion API Helpers ──────────────────────────────────────────────────────
import http.client
import ssl
import socket

# Create a reusable connection to Notion API
_notion_conn = None

def _get_conn():
    global _notion_conn
    try:
        if _notion_conn is not None:
            # Test if connection is still alive
            _notion_conn.sock.getpeername()
    except (AttributeError, OSError, socket.error):
        _notion_conn = None
    
    if _notion_conn is None:
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        _notion_conn = http.client.HTTPSConnection(
            "api.notion.com", timeout=30, context=ctx
        )
    return _notion_conn


def notion_api_get(url, data=None, retries=3):
    """Call Notion API with connection reuse and rate limiting."""
    global _last_api_call
    
    # Rate limiting
    now = time.time()
    since_last = now - _last_api_call
    if since_last < API_DELAY:
        time.sleep(API_DELAY - since_last)
    
    headers = {
        "Authorization": f"Bearer {NOTION_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    for attempt in range(retries):
        try:
            conn = _get_conn()
            
            # Parse URL to get path
            path = url.replace("https://api.notion.com", "")
            
            if data is not None:
                body = json.dumps(data).encode("utf-8")
                conn.request("POST", path, body=body, headers=headers)
            else:
                conn.request("GET", path, headers=headers)
            
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            _last_api_call = time.time()
            
            if not body.strip():
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    print(f"    ⏳ 空响应, {wait}s 后重试 ({attempt+1}/{retries})...")
                    time.sleep(wait)
                    # Reset connection on empty response
                    _notion_conn = None
                    continue
                print(f"    ⚠️  空响应 (重试耗尽)")
                return {}
            
            result = json.loads(body)
            
            if resp.status >= 400:
                err_msg = result.get("message", f"HTTP {resp.status}")
                if "rate" in err_msg.lower() and attempt < retries - 1:
                    wait = 5
                    print(f"    ⏳ 限流: {err_msg[:60]}, {wait}s 后重试...")
                    time.sleep(wait)
                    _notion_conn = None
                    continue
                if resp.status == 409:  # Conflict - transient
                    if attempt < retries - 1:
                        wait = 1
                        time.sleep(wait)
                        continue
                print(f"    ⚠️  API Error ({resp.status}): {err_msg[:120]}")
            
            return result
        except (json.JSONDecodeError, http.client.RemoteDisconnected,
                ConnectionResetError, BrokenPipeError, OSError) as e:
            _notion_conn = None  # Reset connection on error
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"    ⏳ {type(e).__name__}: {e}, {wait}s 后重试...")
                time.sleep(wait)
                continue
            print(f"    ❌ {type(e).__name__}: {e} (重试耗尽)")
            raise
    
    return {}


def notion_api_patch(url, data):
    """PATCH request to Notion API with connection reuse."""
    global _last_api_call
    
    now = time.time()
    since_last = now - _last_api_call
    if since_last < API_DELAY:
        time.sleep(API_DELAY - since_last)
    
    headers = {
        "Authorization": f"Bearer {NOTION_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    
    try:
        conn = _get_conn()
        path = url.replace("https://api.notion.com", "")
        body = json.dumps(data).encode("utf-8")
        conn.request("PATCH", path, body=body, headers=headers)
        resp = conn.getresponse()
        _last_api_call = time.time()
        return json.loads(resp.read().decode("utf-8"))
    except Exception:
        _notion_conn = None
        raise


def get_page_info(page_id):
    return notion_api_get(f"https://api.notion.com/v1/pages/{page_id}")


def get_blocks(block_id, page_size=100):
    """Get all children blocks with pagination."""
    results = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size={page_size}"
        if cursor:
            url += f"&start_cursor={cursor}"
        data = notion_api_get(url)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def query_database(db_id, page_size=100):
    """Query all entries from a database with pagination."""
    results = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/data_sources/{db_id}/query"
        payload = {"page_size": page_size}
        if cursor:
            payload["start_cursor"] = cursor
        data = notion_api_get(url, payload)
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def get_database_properties(db_id):
    """Get database schema (property definitions)."""
    url = f"https://api.notion.com/v1/data_sources/{db_id}"
    data = notion_api_get(url)
    return data.get("properties", {})


# ── Content Extraction ──────────────────────────────────────────────────────
def extract_rich_text(block, btype):
    """Extract plain text from a block's rich_text field."""
    rich_text = block.get(btype, {}).get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in rich_text)


def walk_blocks(parent_block_id, depth=0, page_size=100):
    """Recursively walk blocks and return clean markdown lines.
    Filters out structural comments, condenses dividers, cleans toggles."""
    lines = []
    blocks = get_blocks(parent_block_id, page_size)
    
    for block in blocks:
        btype = block.get("type", "unknown")
        has_children = block.get("has_children", False)
        block_id = block.get("id", "")
        indent = "  " * depth
        line = ""
        
        # ── Heading ──
        if btype in ("heading_1", "heading_2", "heading_3"):
            prefix = "#" * int(btype[-1])
            text = extract_rich_text(block, btype)
            if text.strip():
                line = f"{prefix} {text}"
        
        # ── Paragraph ──
        elif btype == "paragraph":
            text = extract_rich_text(block, btype)
            if text.strip():
                line = text
        
        # ── List items ──
        elif btype == "bulleted_list_item":
            text = extract_rich_text(block, btype)
            children_indent = " " * (depth * 2 + 2)
            line = f"- {text}"
            if has_children:
                child_lines = walk_blocks(block_id, depth + 1, page_size)
                lines.append(line)
                lines.extend(child_lines)
                continue
        
        elif btype == "numbered_list_item":
            text = extract_rich_text(block, btype)
            children_indent = " " * (depth * 2 + 3)
            line = f"1. {text}"
            if has_children:
                child_lines = walk_blocks(block_id, depth + 1, page_size)
                lines.append(line)
                lines.extend(child_lines)
                continue
        
        # ── To-do ──
        elif btype == "to_do":
            checked = block.get("to_do", {}).get("checked", False)
            text = extract_rich_text(block, btype)
            line = f"- [{'x' if checked else ' '}] {text}"
        
        # ── Callout / Quote ──
        elif btype == "callout":
            text = extract_rich_text(block, btype)
            if text.strip():
                line = f"> {text}"
        elif btype == "quote":
            text = extract_rich_text(block, btype)
            if text.strip():
                line = f"> {text}"
        
        # ── Toggle ──
        elif btype == "toggle":
            text = extract_rich_text(block, btype)
            if text.strip():
                line = f"<details><summary>{text}</summary>"
                if has_children:
                    child_lines = walk_blocks(block_id, depth + 1, page_size)
                    lines.append(line)
                    lines.extend(child_lines)
                    lines.append("</details>")
                else:
                    lines.append(f"{line}</details>")
                continue
            elif has_children:
                child_lines = walk_blocks(block_id, depth, page_size)
                lines.extend(child_lines)
                continue
            else:
                continue
        
        # ── Code ──
        elif btype == "code":
            lang = block.get("code", {}).get("language", "")
            text = extract_rich_text(block, btype)
            line = f"```{lang}\n{text}\n```"
        
        # ── Divider — skip if preceded by heading or another divider ──
        elif btype == "divider":
            # Don't add if:
            # 1. Previous line was already a divider
            # 2. Previous line was a heading (headings already provide separation)
            # 3. Previous line was the frontmatter end (---)
            if lines and (lines[-1].strip() == "---" or lines[-1].strip().startswith("# ")):
                continue
            line = "---"
        
        # ── Image ──
        elif btype == "image":
            caption = block.get("image", {}).get("caption", [])
            cap_text = "".join(t.get("plain_text", "") for t in caption)
            if cap_text:
                line = f"*📷 {cap_text}*"
            else:
                line = "*📷 图片*"
        
        # ── Bookmark / Embed ──
        elif btype == "bookmark":
            url = block.get("bookmark", {}).get("url", "")
            text = extract_rich_text(block, btype)
            if text.strip():
                line = f"[🔗 {text.strip()}]({url})"
            else:
                line = f"<{url}>"
        
        elif btype == "embed":
            url = block.get("embed", {}).get("url", "")
            if url:
                line = f"<{url}>"
        
        # ── Video / File / PDF ──
        elif btype in ("video", "file", "pdf"):
            line = f"*[{btype.upper()}]*"
        
        # ── Equation ──
        elif btype == "equation":
            expr = block.get("equation", {}).get("expression", "")
            if expr.strip():
                line = f"$$ {expr} $$"
        
        # ── Table ──
        elif btype == "table":
            if has_children:
                child_lines = walk_blocks(block_id, depth, page_size)
                lines.extend(child_lines)
                continue
        
        elif btype == "table_row":
            cells = block.get("table_row", {}).get("cells", [])
            cell_texts = ["".join(t.get("plain_text", "") for t in cell) for cell in cells]
            line = "| " + " | ".join(cell_texts) + " |"
        
        # ── Structural containers (just unwrap silently) ──
        elif btype in ("column_list", "column", "synced_block"):
            if has_children:
                child_lines = walk_blocks(block_id, depth, page_size)
                lines.extend(child_lines)
                continue
        
        # ── Child database reference ──
        elif btype == "child_database":
            continue  # silently skip child database references
        
        # ── Unknown—skip silently ──
        else:
            continue
        
        if line:
            lines.append(line)
        
        # Recurse into children for most types
        if has_children and btype not in (
            "toggle", "bulleted_list_item", "numbered_list_item",
            "column_list", "column", "synced_block",
            "table"
        ):
            child_lines = walk_blocks(block_id, depth + 1, page_size)
            lines.extend(child_lines)
    
    return lines


def extract_database_properties(properties, property_schema=None):
    """Extract properties from a Notion page into a dict.
    Maps to simple Python types for YAML frontmatter."""
    result = {}
    
    for key, prop in properties.items():
        ptype = prop.get("type", "")
        value = None
        
        if ptype == "title":
            value = "".join(t.get("plain_text", "") for t in prop.get("title", []))
        elif ptype == "rich_text":
            value = "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
        elif ptype == "multi_select":
            value = [opt.get("name", "") for opt in prop.get("multi_select", [])]
        elif ptype == "select":
            sel = prop.get("select")
            value = sel.get("name", "") if sel else None
        elif ptype == "url":
            value = prop.get("url", "") or ""
        elif ptype == "email":
            value = prop.get("email", "") or ""
        elif ptype == "phone_number":
            value = prop.get("phone_number", "") or ""
        elif ptype == "number":
            value = prop.get("number")
        elif ptype == "checkbox":
            value = prop.get("checkbox", False)
        elif ptype == "date":
            date_obj = prop.get("date")
            if date_obj:
                value = {"start": date_obj.get("start"), "end": date_obj.get("end")}
            else:
                value = None
        elif ptype == "created_time":
            value = prop.get("created_time", "")[:10]  # YYYY-MM-DD
        elif ptype == "last_edited_time":
            value = prop.get("last_edited_time", "")[:10]
        elif ptype == "created_by":
            val = prop.get("created_by", {})
            value = val.get("name", "") if val else None
        elif ptype == "unique_id":
            uid = prop.get("unique_id", {})
            if uid:
                number = uid.get("number")
                prefix = uid.get("prefix", "")
                value = f"{prefix}-{number}" if prefix else str(number)
            else:
                value = None
        elif ptype == "status":
            status = prop.get("status")
            value = status.get("name", "") if status else None
        elif ptype == "formula":
            formula = prop.get("formula", {})
            ftype = formula.get("type", "")
            value = formula.get(ftype) if ftype else None
        elif ptype == "rollup":
            rollup = prop.get("rollup", {})
            rtype = rollup.get("type", "")
            value = rollup.get(rtype) if rtype else None
        elif ptype == "relation":
            value = [r.get("id", "") for r in prop.get("relation", [])]
        elif ptype == "people":
            value = [p.get("name", "") for p in prop.get("people", []) if p.get("name")]
        elif ptype == "files":
            value = [f.get("name", "") for f in prop.get("files", [])]
        elif ptype == "phone_number":
            value = prop.get("phone_number", "")
        # skip internal properties
        else:
            continue
        
        if value is not None and value != "" and value != [] and value != {}:
            result[key] = value
    
    return result


def sanitize_filename(name, max_len=80):
    """Convert a page title to a safe filename."""
    # Remove problematic characters
    name = re.sub(r'[\\/:*?"<>|~^]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    # Truncate
    if len(name) > max_len:
        name = name[:max_len].rsplit(' ', 1)[0]
    return name


def file_safe_title(title):
    """Create a file-safe version of the title for the filename.
    Preserves common characters, only removes truly invalid ones."""
    safe = title.strip()
    # Replace spaces with underscores
    safe = safe.replace(" ", "_")
    # Remove only truly OS-invalid characters
    safe = re.sub(r'[\\/:*"<>|]', '', safe)
    if not safe or safe == '_':
        safe = "untitled"
    return safe[:80]


# ── Markdown Generation ─────────────────────────────────────────────────────
def generate_markdown(title, properties, content_lines, source_type="article"):
    """Generate clean markdown with YAML frontmatter (no empty values)."""
    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Build frontmatter - only non-empty values
    frontmatter = {
        "title": title,
    }
    
    # Add properties (skip empty values and internal fields)
    skip_keys = {"在本项目中", "created_time", "名称", "ID"}
    for key, value in properties.items():
        if key in skip_keys:
            continue
        # Skip empty values
        if value is None or value == "" or value == [] or value == {}:
            continue
        frontmatter[key] = value
    
    # Always add notion_id and sync timestamp
    if properties.get("notion_id"):
        frontmatter["notion_id"] = properties["notion_id"]
    frontmatter["synced_at"] = now
    
    # Serialize frontmatter to YAML
    yaml_lines = ["---"]
    for key, value in frontmatter.items():
        yaml_lines.append(yaml_value(key, value))
    yaml_lines.append("---")
    
    # Clean content: remove leading/trailing blank lines
    content = content_lines if isinstance(content_lines, str) else "\n".join(content_lines)
    content = content.strip()
    
    if not content:
        return "\n".join(yaml_lines) + "\n"
    
    return "\n".join(yaml_lines) + "\n\n" + content + "\n"


def yaml_value(key, value, indent=0):
    """Serialize a value to YAML format."""
    prefix = "  " * indent
    if isinstance(value, dict):
        lines = [f"{prefix}{key}:"]
        for k, v in value.items():
            lines.append(yaml_value(k, v, indent + 1))
        return "\n".join(lines)
    elif isinstance(value, list):
        if not value:
            return f"{prefix}{key}: []"
        items = "\n".join(f"{prefix}  - {json.dumps(v, ensure_ascii=False)}" for v in value)
        return f"{prefix}{key}:\n{items}"
    elif isinstance(value, bool):
        return f"{prefix}{key}: {'true' if value else 'false'}"
    elif isinstance(value, (int, float)):
        return f"{prefix}{key}: {value}"
    elif value is None:
        return f"{prefix}{key}:"
    else:
        # String - use quotes if needed
        s = str(value)
        if any(c in s for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`']):
            return f"{prefix}{key}: {json.dumps(s, ensure_ascii=False)}"
        return f"{prefix}{key}: {s}"


# ── File Operations ─────────────────────────────────────────────────────────
def save_mapping(mapping):
    with open(MAPPING_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"  📍 映射文件已保存: _mapping.json ({len(mapping)} 条)")


def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_sync": None, "file_hashes": {}}


def file_hash(path):
    """MD5 hash of a file's content."""
    if not os.path.exists(path):
        return None
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_all_files(repo_path):
    """Get all .md files in the repo (excluding _ prefixed)."""
    files = []
    for root, dirs, dirnames in os.walk(repo_path):
        # Skip hidden dirs and _ prefixed files
        dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("_")]
        for fn in dirnames:
            if fn.endswith(".md"):
                files.append(os.path.join(root, fn))
    return files


# ── Main Sync Logic: Notion → GitHub ────────────────────────────────────────
def sync_notion_to_github():
    """Extract all content from Notion and save to GitHub repo."""
    print("=" * 60)
    print("  📥 Notion → GitHub 同步")
    print("=" * 60)
    print()
    
    mapping = {}
    stats = {"articles": 0, "tools": 0, "communities": 0, "errors": 0}
    
    # ── Create output directories ──
    articles_dir = os.path.join(REPO_PATH, "articles")
    tools_dir = os.path.join(REPO_PATH, "curations", "tools")
    communities_dir = os.path.join(REPO_PATH, "curations", "communities")
    os.makedirs(articles_dir, exist_ok=True)
    os.makedirs(tools_dir, exist_ok=True)
    os.makedirs(communities_dir, exist_ok=True)
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    
    # ── Step 1: Extract child pages from main page (articles) ──
    print("📄 提取文章页面...")
    child_blocks = get_blocks(MAIN_PAGE_ID)
    child_pages = [b for b in child_blocks if b.get("type") == "child_page"]
    
    for i, page_block in enumerate(child_pages):
        page_id = page_block.get("id", "")
        title = page_block.get("child_page", {}).get("title", "Untitled")
        print(f"  [{i+1}/{len(child_pages)}] {title}...", end=" ", flush=True)
        
        try:
            # Get page info for properties
            page_info = get_page_info(page_id)
            props = page_info.get("properties", {})
            
            # Extract created/last edited time
            created_time = props.get("created_time", {}).get("created_time", "")[:10] if "created_time" in props else ""
            last_edited = page_info.get("last_edited_time", "")[:10]
            
            # Extract content using notion-to-md (Node.js) for better quality
            n2m_script = os.path.join(SCRIPTS_DIR, "n2m-convert.js")
            try:
                r = subprocess.run(
                    ["node", n2m_script, page_id],
                    capture_output=True, text=True, timeout=60
                )
                if r.returncode == 0 and r.stdout.strip():
                    md_content = r.stdout.strip()
                else:
                    # Fallback to Python walker
                    print(f"⚠️  n2m fell back, using Python walker...")
                    content_lines = walk_blocks(page_id)
                    md_content = "\n".join(content_lines) if content_lines else ""
            except Exception as e:
                print(f"⚠️  n2m error ({e}), using Python walker...")
                content_lines = walk_blocks(page_id)
                md_content = "\n".join(content_lines) if content_lines else ""
            
            # Build properties
            properties = {
                "notion_id": page_id,
                "last_edited_time": last_edited,
            }
            
            # Generate markdown
            md = generate_markdown(title, properties, md_content, "article")
            
            # Save file (overwrite if exists)
            safe_name = file_safe_title(title)
            filepath = os.path.join(articles_dir, f"{safe_name}.md")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            
            # Track mapping
            mapping[page_id] = os.path.relpath(filepath, REPO_PATH)
            stats["articles"] += 1
            print("✅")
            
        except Exception as e:
            print(f"❌ {e}")
            stats["errors"] += 1
    
    print()
    
    # ── Step 2: Extract tools database ──
    print("🛠️  提取工具数据库...")
    tool_entries = query_database(TOOLS_DB_ID)
    tool_props_schema = get_database_properties(TOOLS_DB_ID)
    
    for i, entry in enumerate(tool_entries):
        entry_id = entry.get("id", "")
        props = entry.get("properties", {})
        page_info = get_page_info(entry_id)
        last_edited = page_info.get("last_edited_time", "")[:10]
        
        # Extract title
        title = ""
        for key, prop in props.items():
            if prop.get("type") == "title":
                title = "".join(t.get("plain_text", "") for t in prop.get("title", []))
                break
        if not title:
            title = "Untitled Tool"
        
        print(f"  [{i+1}/{len(tool_entries)}] {title}...", end=" ", flush=True)
        
        try:
            # Extract database properties
            db_props = extract_database_properties(props, tool_props_schema)
            db_props["notion_id"] = entry_id
            db_props["last_edited_time"] = last_edited
            
            # Extract content (if any)
            content_lines = walk_blocks(entry_id)
            if not content_lines:
                content_lines = []
            if "用途" in db_props:
                usage_text = db_props.get("用途", "")
                if usage_text and not content_lines:
                    content_lines = [usage_text]
            
            # Generate markdown
            md = generate_markdown(title, db_props, content_lines, "tool")
            
            # Save file
            safe_name = file_safe_title(title)
            filepath = os.path.join(tools_dir, f"{safe_name}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            
            mapping[entry_id] = os.path.relpath(filepath, REPO_PATH)
            stats["tools"] += 1
            print("✅")
            
        except Exception as e:
            print(f"❌ {e}")
            stats["errors"] += 1
    
    print()
    
    # ── Step 3: Extract community database ──
    print("🌐 提取社区数据库...")
    community_entries = query_database(COMMUNITY_DB_ID)
    
    for i, entry in enumerate(community_entries):
        entry_id = entry.get("id", "")
        props = entry.get("properties", {})
        page_info = get_page_info(entry_id)
        last_edited = page_info.get("last_edited_time", "")[:10]
        
        # Extract title
        title = ""
        for key, prop in props.items():
            if prop.get("type") == "title":
                title = "".join(t.get("plain_text", "") for t in prop.get("title", []))
                break
        if not title:
            title = "Untitled Community"
        
        print(f"  [{i+1}/{len(community_entries)}] {title}...", end=" ", flush=True)
        
        try:
            db_props = extract_database_properties(props)
            db_props["notion_id"] = entry_id
            db_props["last_edited_time"] = last_edited
            
            content_lines = walk_blocks(entry_id)
            if not content_lines:
                content_lines = []
            
            md = generate_markdown(title, db_props, content_lines, "community")
            
            safe_name = file_safe_title(title)
            filepath = os.path.join(communities_dir, f"{safe_name}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            
            mapping[entry_id] = os.path.relpath(filepath, REPO_PATH)
            stats["communities"] += 1
            print("✅")
            
        except Exception as e:
            print(f"❌ {e}")
            stats["errors"] += 1
    
    # ── Save mapping & state ──
    save_mapping(mapping)
    
    state = {
        "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "file_hashes": {},
    }
    for page_id, relpath in mapping.items():
        fullpath = os.path.join(REPO_PATH, relpath)
        if os.path.exists(fullpath):
            state["file_hashes"][relpath] = file_hash(fullpath)
    save_state(state)
    
    print()
    print("=" * 60)
    print(f"  📊 同步统计:")
    print(f"    文章: {stats['articles']} 篇")
    print(f"    工具: {stats['tools']} 个")
    print(f"    社区: {stats['communities']} 个")
    print(f"    错误: {stats['errors']}")
    print("=" * 60)
    
    return stats


# ── Git Operations ──────────────────────────────────────────────────────────
def git_commit_and_push(message):
    """Git add, commit, push."""
    os.chdir(REPO_PATH)
    
    # Check if there are changes
    r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if not r.stdout.strip():
        print("  ℹ️  没有变更，跳过 commit")
        return True
    
    subprocess.run(["git", "add", "-A"], capture_output=True)
    r = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    print(f"  📝 {r.stdout.strip()}")
    
    if not DRY_RUN:
        r = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print("  🚀 已推送到 GitHub")
        else:
            print(f"  ⚠️  Push 可能失败: {r.stderr[:200]}")
    else:
        print("  🏃 Dry-run 模式，跳过 push")
    
    return True


# ── Reverse Sync: GitHub → Notion (bidirectional) ──────────────────────────
def sync_github_to_notion():
    """Check repo for file changes and update corresponding Notion pages."""
    print("=" * 60)
    print("  📤 GitHub → Notion 同步")
    print("=" * 60)
    print()
    
    mapping = load_mapping()
    state = load_state()
    previous_hashes = state.get("file_hashes", {})
    
    if not mapping:
        print("❌ 没有映射文件，请先运行正向同步 (Notion → GitHub)")
        return False
    
    changes = 0
    errors = 0
    
    for page_id, relpath in mapping.items():
        fullpath = os.path.join(REPO_PATH, relpath)
        
        if not os.path.exists(fullpath):
            print(f"  ⚠️  文件不存在 (已删除?): {relpath}")
            continue
        
        new_hash = file_hash(fullpath)
        old_hash = previous_hashes.get(relpath)
        
        if new_hash == old_hash:
            continue  # No change
        
        print(f"  📝 变更检测: {relpath}...", end=" ", flush=True)
        
        try:
            # Read the markdown file
            with open(fullpath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract title from frontmatter
            title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip().strip('"').strip("'") if title_match else os.path.basename(relpath).replace(".md", "")
            
            # TODO: For full bidirectional sync, we'd parse the markdown back into 
            # Notion blocks and update via the API. For now, just update the page title.
            
            # Update Notion page title
            payload = {
                "properties": {
                    "title": {
                        "title": [{"text": {"content": title}}]
                    }
                }
            }
            result = notion_api_patch(f"https://api.notion.com/v1/pages/{page_id}", payload)
            
            if "error" not in result:
                print("✅ 标题已更新")
                changes += 1
            else:
                print(f"⚠️ {result.get('message', '未知错误')[:60]}")
                errors += 1
        
        except Exception as e:
            print(f"❌ {e}")
            errors += 1
    
    print()
    print(f"  更新: {changes} 个, 错误: {errors}")
    
    # Update state
    state["file_hashes"] = {}
    for pid, rp in mapping.items():
        fp = os.path.join(REPO_PATH, rp)
        if os.path.exists(fp):
            state["file_hashes"][rp] = file_hash(fp)
    state["last_sync"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_state(state)
    
    return True


# ── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if REVERSE:
        sync_github_to_notion()
    else:
        stats = sync_notion_to_github()
        
        # Always commit after sync (unless dry-run)
        if not DRY_RUN:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            git_commit_and_push(f"🔄 Notion 同步 ({today}): {stats['articles']}篇, {stats['tools']}工具, {stats['communities']}社区")
        else:
            print("\n🏃 Dry-run 模式: 文件已提取但未推送")
