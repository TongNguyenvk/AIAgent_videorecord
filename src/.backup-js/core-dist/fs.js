import { renameSync, copyFileSync, rmSync } from "node:fs";
/**
 * Move a file from `src` to `dest`, falling back to copy+delete when the
 * source and destination reside on different devices (`EXDEV`).
 */
export function moveFileSync(src, dest) {
    try {
        renameSync(src, dest);
    }
    catch (err) {
        if (err.code === "EXDEV") {
            copyFileSync(src, dest);
            rmSync(src, { force: true });
        }
        else {
            throw err;
        }
    }
}
//# sourceMappingURL=fs.js.map