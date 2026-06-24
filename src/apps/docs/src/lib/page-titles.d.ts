/**
 * Single source of truth for page titles.
 * Used by both page metadata exports and the OG image route.
 *
 * Keys mirror the page's URL path (e.g. "commands" -> /og/commands).
 * Values are display titles (without the "| webreel" suffix; the layout template adds that).
 */
export declare const PAGE_TITLES: Record<string, string>;
/**
 * Get the page title for a given slug.
 * Returns null if the slug is not in the whitelist.
 */
export declare function getPageTitle(slug: string): string | null;
//# sourceMappingURL=page-titles.d.ts.map