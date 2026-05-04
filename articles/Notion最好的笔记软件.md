---
title: "Notion~最好的笔记(?)软件"
source: article
notion_synced_at: "2026-05-04T11:33:11Z"
notion_id: "b7366ad7-c9c4-8272-9a01-017ec58fd83a"
created_time: 
last_edited_time: "2026-05-04"
---

## 介绍
https://www.notion.so/
---
本页面介绍 Notion的基础使用方法
> Notion 在持续更新中，本页面内容可能更新不及时，请以实际体验为准。
### ToDo
  本页面待完善的部分
  - [ ] 模板 
  - [ ] Notion API和连接 
  - [ ] 多人协作 
  - [ ] AI 
  - [ ] Tips 
---
- Notion 是一款 All-in-one 的笔记(?)软件。
- 如果你在各种平台搜索或问各种 AI 最好的笔记软件是哪个，那么得到的内容中几乎必定包含 Notion。
- Notion 的用途几乎没有限制，只取决于你的想象力。
- Notion 能实现无限嵌套、随意链接、内容转换等等多种复杂功能。
- 请注意，Notion 并不是完美的，祂也有缺点，比如打开速度比较慢等，所以 Notion 可能不适合所有人。
  > notionfaster 是一个通过反向代理加速国内 Notion 访问速度的工具
  如果你不喜欢 Notion，也有很多很优秀的笔记软件，例如 Obsidian、Typora、Evernote（印象笔记）等，希望你找到最适合自己的。
- 另外,本项目就是基于 notion 打造的。
# 使用
---
Notion 可以用于笔记记录、任务管理、项目规划和团队协作。它提供了一个灵活的平台，可以创建和组织各种类型的内容，如文字、表格、看板和日历。
Notion 网页端使用体验相对完整，Windows 桌面应用基本套壳浏览器，手机App 基本只能看不能写适合简单记录，不适合长篇写作，所以推荐日常使用网页端。
> 可选：Notion Boost 是一个增强 Notion 使用体验的浏览器拓展，Notion 生态还有更多实用项目，可以自行探索
  [🔗 https://gourav.io/notion-boost](https://gourav.io/notion-boost)
## 视频教程
  如果你不喜欢看大段文字，可以结合这些视频教程入门
  - 全世界在抄的软件，到底怎么用？Notion十分钟入门指南。
    [🔗 https://www.bilibili.com/video/av936863800](https://www.bilibili.com/video/av936863800)
  - 玩转Notion，你需要这份2024新手指南（建议收藏）
    [🔗 https://www.bilibili.com/video/BV1uM4m1m7oJ](https://www.bilibili.com/video/BV1uM4m1m7oJ)
  - B 站最强 Notion 测评，极致丝滑！新手进阶必看 16 个教程用法丨笔记软件推荐
    [🔗 https://www.bilibili.com/video/av300480490](https://www.bilibili.com/video/av300480490)
---
## 块和快捷键
  Notion 以块为单位组织页面，一个块可以是一行文本，一个提及链接，一个页面等等
  输入 / 可以展示所有可用的块，继续输入可用英文搜索，如输入 /code 可展示代码相关的块，也可转换光标所在行为相应的块。
  ---
  Notion的每个块都可以链接，选中文本时可粘贴超链接，未选中时可以多种形式粘贴网页链接。
  Notion 的所有操作几乎都有快捷键,熟练掌握快捷键可大大提升工作效率。
  如果你不喜欢用快捷键，Notion 的所有操作也几乎可以用鼠标完成。
  - 复制：ctrl + C
  - 粘贴(链接)：ctrl + V 
  - 打开快速搜索：ctrl + P
  - 切换黑暗模式：ctrl + Shift + L
  - 添加新行/块：shift + Enter
  - 缩进/补全：Tab
  - 取消缩进：shift + Tab
  - 分割线：--- 
  - 复制当前行/块：ctrl + D
  - 撤销：ctrl + Z
  - 重做：ctrl + Y / ctrl + shift + z
  - 插入日期/时间/链接/提及：@ （有时需要 space + @ 或 @ + space ）
  - 多级标题: # + Space
  - 折叠: > + Space
  - 代码块: ctrl + E
  - 数学公式: ctrl + shift + E    
  - 加粗:  ctrl + B
  - 斜体: ctrl + I
  - 查找: ctrl + F
  - 搜索操作：Ctrl + / 
  > 更多快捷键请参考以下页面
    [🔗 https://www.notion.so/zh-cn/help/keyboard-shortcuts](https://www.notion.so/zh-cn/help/keyboard-shortcuts)
    [🔗 https://docs.tangly1024.com/article/notion-short-key](https://docs.tangly1024.com/article/notion-short-key)
---
## 页面布局
  ---
  <!-- COLUMN_LIST -->
  <!-- COLUMN -->
    Notion 以页面为基础，一个页面可以有多种存在形式，也可以链接到其他地方。
    每个页面都可以添加图标和封面，可用于展示。
    每个页面的右上角都有一些信息，包括评论，更新日志，收藏和页面设置。
  <!-- /COLUMN -->
  <!-- COLUMN -->
    ![页面右上角的按钮示例](IMAGE_PLACEHOLDER)
  <!-- /COLUMN -->
  <!-- /COLUMN_LIST -->
---
## 数据库
  Notion 的数据库十分强大,一个数据库可以多种视图呈现。
  数据库可以用于组织和管理各种类型的信息，如项目任务、联系人列表、资产清单等。常见的视图包括表格视图、看板视图、日历视图和画廊视图。每种视图都可以根据特定需求进行自定义，以便更有效地展示和分析数据。
  ---
  1. 使用 / 命令插入可选择视图以插入数据库，数据库内还可创建单独的页面模板。
  1. 表格是最基本的数据库，就像 Excel 表格一样，每一列都是一个属性，每一行都是一个页面。你可以自定义属性类型，如文本、数字、日期、多选等，以满足不同的数据需求。
  1. 筛选器、排序和群组可以处理视图要如何展示、展示哪些数据，对于不同视图有不同的展示效果，善用这三个功能可以让排版更优美。
  <!-- CHILD_DATABASE -->
---
## 模板
  Notion 的模板已经成为一个庞大的生态,许多需求都可以找到对应的模板
  Notion 提供了大量免费和付费模板，涵盖了各种用途，如项目管理、个人生活规划、学习笔记等。用户可以直接使用这些模板，也可以根据自己的需求进行修改和定制。此外，Notion 社区中也有许多用户分享的高质量模板，为用户提供了更多选择。
---
## Notion API和连接
---
## 多人协作
  Notion 拥有强大的多人协作能力，为不同价位的用户提供不同服务。
  一个页面的子页面会继承人员权限，也可以单独设置子页面的人员权限
  <details><summary>各方案详细权限</summary>
  

    ![Notion 为各个价位的用户提供了方案等级森严](IMAGE_PLACEHOLDER)
  </details>
  ---
  - 对于免费用户
    一个页面可添加10位访客一同编辑，该页面下的页面会继承访客。
    可以点击页面右上角的分享按钮，输入拥有 Notion 账号的邮箱。
    使用 @ 命令可以达到同样的效果。
    > 如果邀请为成员，则每个页面的区块数量有限制。
      另外，可以通过共享一个账户的方式达到多人协作的部分效果，但是此方法有诸多限制。
  - 对于付费用户
    notion 
---
## AI
  Notion 的 AI 功能非常强大且易于使用。(免费用户使用额度有限)
  它可以快速生成内容、总结长文本、翻译语言，甚至协助创建数据库和页面结构，大大提高工作效率，特别是在处理大量信息或需要创意灵感时。
---
## Tips
  以下是一些使用 Notion 的实用技巧：
  - 格式习惯：使用 --- 分割线和空行辅助排版，下划线分割歧义词，加粗强调等，推荐熟练使用这些常用操作的快捷键。
  - 数据结构：编写时明确数据的结构很重要，例如本项目只使用一个数据库，在页面下方设置原始表格，上方所有视图都连接到该数据库，以实现简洁的项目管理。
  - 善用模板：利用 Notion 提供的模板或社区分享的模板，可以快速搭建项目框架，节省大量时间。
  - 嵌套页面：充分利用 Notion 的嵌套功能，将相关内容组织在一起，便于管理和查找，但不建议嵌套多层页面，避免内容混乱。
---
## 示例
  来自互联网的一些 Notion 使用示例
  ![](IMAGE_PLACEHOLDER)
  关于Notion的更多使用方法可以去B站等平台搜索 Notion 教程自行探索。
---
## 推荐项目
此处列举一些有助于使用 notion 的工具
- 阿里巴巴矢量图标库
  [🔗 https://www.iconfont.cn/](https://www.iconfont.cn/)
- Awesome 图标库
  [🔗 https://fontawesome.com/](https://fontawesome.com/)
此处列举一些基于 Notion 的项目。
-  使用 NextJS + Notion API 实现的，支持多种部署方案的静态博客，无需服务器、零门槛搭建网站，为Notion和所有创作者设计。
-  将微信读书划线同步到Notion
