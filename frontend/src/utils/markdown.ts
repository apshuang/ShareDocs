import TurndownService from 'turndown'
import { marked } from 'marked'

const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-',
})

marked.setOptions({
  breaks: true,
  gfm: true,
})

export function htmlToMarkdown(html: string): string {
  return turndownService.turndown(html)
}

export function markdownToHtml(markdown: string): string {
  return marked.parse(markdown, { breaks: true, gfm: true }) as string
}

