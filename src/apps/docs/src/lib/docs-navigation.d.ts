export type NavItem = {
    title: string;
    href: string;
    external?: boolean;
};
export type NavSection = {
    title: string;
    items: NavItem[];
};
export declare const docsNavigation: NavSection[];
export declare const allDocsPages: NavItem[];
//# sourceMappingURL=docs-navigation.d.ts.map