/**
 * Converts raw MDX content to clean Markdown suitable for AI agents.
 *
 * Transformations:
 * - Remove `export` statements (metadata, etc.)
 * - Remove `import` statements
 * - Strip standalone JSX divs with className attributes
 * - Pass everything else through as-is (already valid Markdown)
 */
export declare function mdxToCleanMarkdown(raw: string): string;
//# sourceMappingURL=mdx-to-markdown.d.ts.map