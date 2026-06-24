import * as React from "react";
import * as SheetPrimitive from "@radix-ui/react-dialog";
declare const Sheet: React.FC<SheetPrimitive.DialogProps>;
declare const SheetTrigger: React.ForwardRefExoticComponent<SheetPrimitive.DialogTriggerProps & React.RefAttributes<HTMLButtonElement>>;
declare const SheetContent: React.ForwardRefExoticComponent<Omit<SheetPrimitive.DialogContentProps & React.RefAttributes<HTMLDivElement>, "ref"> & {
    side?: "left" | "right";
    overlayClassName?: string;
} & React.RefAttributes<HTMLDivElement>>;
declare const SheetTitle: React.ForwardRefExoticComponent<Omit<SheetPrimitive.DialogTitleProps & React.RefAttributes<HTMLHeadingElement>, "ref"> & React.RefAttributes<HTMLHeadingElement>>;
export { Sheet, SheetTrigger, SheetContent, SheetTitle };
//# sourceMappingURL=sheet.d.ts.map