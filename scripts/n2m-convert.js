#!/usr/bin/env node
/**
 * Notion page → Markdown converter
 * Uses notion-to-md for high-quality block conversion.
 * 
 * Usage: node n2m-convert.js <page_id>
 * Outputs markdown string to stdout.
 * 
 * Errors: exits with non-zero, error message to stderr.
 */
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

async function main() {
  const pageId = process.argv[2];
  if (!pageId) {
    console.error("Usage: node n2m-convert.js <page_id>");
    process.exit(1);
  }

  try {
    const mdBlocks = await n2m.pageToMarkdown(pageId, 100);
    const mdString = n2m.toMarkdownString(mdBlocks);
    const content = mdString.parent || "";
    
    // Post-process: clean up excessive blank lines
    // notion-to-md produces many double/triple newlines
    const cleaned = content
      .replace(/\n{3,}/g, "\n\n")   // 3+ blank lines → 2
      .replace(/^\n+/, "")           // leading blank lines
      .replace(/\n+$/, "")           // trailing blank lines
      .trim();
    
    process.stdout.write(cleaned);
  } catch (e) {
    console.error(`N2M_ERROR: ${e.message}`);
    process.exit(1);
  }
}

main();
