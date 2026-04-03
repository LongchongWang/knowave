import { defineConfig } from 'vitepress'
import { generateSidebar } from 'vitepress-sidebar'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Knowave",
  description: "Knowledge Wave",
  srcDir: 'knowledge',
  cleanUrls: true,
  ignoreDeadLinks: true,
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
  }
})
