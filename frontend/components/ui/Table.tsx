import React, { forwardRef } from "react";
import styles from "./Table.module.css";

/* -----------------------------------------------------------------------------
   Table Root (Wrapped in responsive scroll container)
   ----------------------------------------------------------------------------- */
export interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  wrapperClassName?: string;
}

export const Table = forwardRef<HTMLTableElement, TableProps>(
  ({ className = "", wrapperClassName = "", children, ...props }, ref) => {
    return (
      <div className={`${styles.wrapper} ${wrapperClassName}`.trim()} role="region" aria-label="Data Table">
        <table ref={ref} className={`${styles.table} ${className}`.trim()} {...props}>
          {children}
        </table>
      </div>
    );
  }
);

Table.displayName = "Table";

/* -----------------------------------------------------------------------------
   TableHeader (thead)
   ----------------------------------------------------------------------------- */
export type TableHeaderProps = React.HTMLAttributes<HTMLTableSectionElement>;

export const TableHeader = forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <thead ref={ref} className={`${styles.header} ${className}`.trim()} {...props}>
        {children}
      </thead>
    );
  }
);

TableHeader.displayName = "TableHeader";

/* -----------------------------------------------------------------------------
   TableBody (tbody)
   ----------------------------------------------------------------------------- */
export type TableBodyProps = React.HTMLAttributes<HTMLTableSectionElement>;

export const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <tbody ref={ref} className={`${styles.tbody} ${className}`.trim()} {...props}>
        {children}
      </tbody>
    );
  }
);

TableBody.displayName = "TableBody";

/* -----------------------------------------------------------------------------
   TableFooter (tfoot)
   ----------------------------------------------------------------------------- */
export type TableFooterProps = React.HTMLAttributes<HTMLTableSectionElement>;

export const TableFooter = forwardRef<HTMLTableSectionElement, TableFooterProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <tfoot ref={ref} className={`${styles.footer} ${className}`.trim()} {...props}>
        {children}
      </tfoot>
    );
  }
);

TableFooter.displayName = "TableFooter";

/* -----------------------------------------------------------------------------
   TableRow (tr)
   ----------------------------------------------------------------------------- */
export type TableRowProps = React.HTMLAttributes<HTMLTableRowElement>;

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <tr ref={ref} className={`${styles.row} ${className}`.trim()} {...props}>
        {children}
      </tr>
    );
  }
);

TableRow.displayName = "TableRow";

/* -----------------------------------------------------------------------------
   TableHead (th)
   ----------------------------------------------------------------------------- */
export type TableHeadProps = React.ThHTMLAttributes<HTMLTableCellElement>;

export const TableHead = forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ className = "", scope = "col", children, ...props }, ref) => {
    return (
      <th ref={ref} scope={scope} className={`${styles.th} ${className}`.trim()} {...props}>
        {children}
      </th>
    );
  }
);

TableHead.displayName = "TableHead";

/* -----------------------------------------------------------------------------
   TableCell (td)
   ----------------------------------------------------------------------------- */
export type TableCellProps = React.TdHTMLAttributes<HTMLTableCellElement>;

export const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <td ref={ref} className={`${styles.td} ${className}`.trim()} {...props}>
        {children}
      </td>
    );
  }
);

TableCell.displayName = "TableCell";

/* -----------------------------------------------------------------------------
   TableCaption (caption)
   ----------------------------------------------------------------------------- */
export type TableCaptionProps = React.HTMLAttributes<HTMLTableCaptionElement>;

export const TableCaption = forwardRef<HTMLTableCaptionElement, TableCaptionProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <caption ref={ref} className={`${styles.caption} ${className}`.trim()} {...props}>
        {children}
      </caption>
    );
  }
);

TableCaption.displayName = "TableCaption";
