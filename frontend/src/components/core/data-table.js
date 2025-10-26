"use client";

import Checkbox from "@mui/material/Checkbox";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";

export function DataTable({
	columns,
	hideHead,
	hover,
	onClick,
	onDeselectAll,
	onDeselectOne,
	onSelectOne,
	onSelectAll,
	onSortChange,
	rows,
	selectable,
	selected,
	sortState,
	uniqueRowId,
	...props
}) {
	const selectedSome = (selected?.size ?? 0) > 0 && (selected?.size ?? 0) < rows.length;
	const selectedAll = rows.length > 0 && selected?.size === rows.length;

	return (
		<Table {...props}>
			<TableHead sx={{ ...(hideHead && { visibility: "collapse", "--TableCell-borderWidth": 0 }) }}>
				<TableRow>
					{selectable ? (
						<TableCell padding="checkbox" sx={{ width: "40px", minWidth: "40px", maxWidth: "40px" }}>
							<Checkbox
								checked={selectedAll}
								indeterminate={selectedSome}
								onChange={(event) => {
									if (selectedAll) {
										onDeselectAll?.(event);
									} else {
										onSelectAll?.(event);
									}
								}}
							/>
						</TableCell>
					) : null}
					{columns.map((column) => {
						const sortable = Boolean(column.sortable);
						const columnKey = column.sortKey ?? column.key ?? column.name;
						const isActive = sortable && sortState?.orderBy === columnKey;
						const direction = isActive ? (sortState?.order ?? "asc") : "asc";
						return (
							<TableCell
								key={column.key ?? column.name}
								sx={{
									width: column.width,
									minWidth: column.width,
									maxWidth: column.width,
									...(column.align && { textAlign: column.align }),
								}}
							>
								{column.hideName ? null : sortable ? (
									<TableSortLabel
										active={isActive}
										direction={direction}
										hideSortIcon={!isActive}
										onClick={() => {
											if (!onSortChange) return;
											const nextDirection = isActive && direction === "asc" ? "desc" : "asc";
											onSortChange({
												column,
												order: nextDirection,
												orderBy: columnKey,
											});
										}}
									>
										{column.name}
									</TableSortLabel>
								) : (
									column.name
								)}
							</TableCell>
						);
					})}
				</TableRow>
			</TableHead>
			<TableBody>
				{rows.map((row, index) => {
					const rowId = row.id ?? uniqueRowId?.(row);
					const rowSelected = rowId ? selected?.has(rowId) : false;

					return (
						<TableRow
							hover={hover}
							key={rowId ?? index}
							selected={rowSelected}
							{...(onClick && {
								onClick: (event) => {
									onClick(event, row);
								},
							})}
							sx={{ ...(onClick && { cursor: "pointer" }) }}
						>
							{selectable ? (
								<TableCell padding="checkbox">
									<Checkbox
										checked={rowId ? rowSelected : false}
										onChange={(event) => {
											if (rowSelected) {
												onDeselectOne?.(event, row);
											} else {
												onSelectOne?.(event, row);
											}
										}}
										onClick={(event) => {
											if (onClick) {
												event.stopPropagation();
											}
										}}
									/>
								</TableCell>
							) : null}
							{columns.map((column) => (
								<TableCell key={column.key ?? column.name} sx={{ ...(column.align && { textAlign: column.align }) }}>
									{column.formatter ? column.formatter(row, index) : column.field ? row[column.field] : null}
								</TableCell>
							))}
						</TableRow>
					);
				})}
			</TableBody>
		</Table>
	);
}
