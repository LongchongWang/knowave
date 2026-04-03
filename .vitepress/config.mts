import { defineConfig } from 'vitepress'
import { generateSidebar } from 'vitepress-sidebar'
import type { UserConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Knowave",
  description: "Knowledge Wave",
  srcDir: 'knowledge',
  cleanUrls: true,
  ignoreDeadLinks: true,
  lastUpdated: true,
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: '文档', link: '/' }
    ],

    sidebar: generateSidebar({
      scanStartPath: 'knowledge',
      resolvePath: '/',
      useTitleFromFrontmatter: true,
      useFolderTitleFromIndexFile: false,
      collapsed: false,
    })
  },
  // 自定义主题扩展
  transformPageData(pageData) {
    return {
      frontmatter: {
        ...pageData.frontmatter,
        layout: 'doc'
      }
    }
  }
})
