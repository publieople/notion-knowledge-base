const { NotionToMarkdown } = require("notion-to-md");
const { Client } = require("@notionhq/client");
const fs = require("fs");
const path = require("path");

const NOTION_KEY = fs.readFileSync(
  path.join(process.env.HOME, ".config/notion/api_key"),
  "utf8"
).trim();

const notion = new Client({ auth: NOTION_KEY, notionVersion: "2025-09-03" });
const n2m = new NotionToMarkdown({ notionClient: notion });

async function test(pageId, label) {
  console.log(`\n=== ${label} (${pageId}) ===`);
  try {
    const mdBlocks = await n2m.pageToMarkdown(pageId, 100);
    const mdString = n2m.toMarkdownString(mdBlocks);
    const content = mdString.parent || "";
    console.log(content.substring(0, 800));
    console.log(`... (${content.length} chars total)`);
    
    // Check for any child pages
    const childKeys = Object.keys(mdString).filter(k => k !== "parent");
    if (childKeys.length > 0) {
      console.log(`  Child pages: ${childKeys.join(", ")}`);
    }
  } catch (e) {
    console.error(`  ERROR: ${e.message.substring(0, 100)}`);
  }
}

async function main() {
  // Test a few different page types
  await test("b4266ad7-c9c4-83ee-b5d9-0163d8cff4b2", "优雅的文件管理 (article)");
  await test("9ed66ad7-c9c4-83cf-8390-81223d50a9fd", "电脑高手速成班 (article)");
  await test("0bb66ad7-c9c4-8397-90cd-01e8486a47e7", "AI 带来了什么 (article)");
  await test("c5266ad7-c9c4-82d1-9562-817a9cca5e76", "Windows桌面环境美化 (article)");
  await test("81866ad7-c9c4-83f5-afca-814915d1c399", "Bilibili (community)");
  await test("03066ad7-c9c4-8201-9097-0132ea40b974", "Open Alternative (tool)");
}

main().catch(console.error);
