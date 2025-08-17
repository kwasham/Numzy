"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import OutlinedInput from "@mui/material/OutlinedInput";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { paths } from "@/paths";
import { FilterButton, FilterPopover, useFilterContext } from "@/components/core/filter-button";
import { Option } from "@/components/core/option";

import { useReceiptsSelection } from "./receipts-selection-context";

export function ReceiptsFilters({ filters = {}, sortDir = "desc", statusCounts }) {
	const { merchant, id, status } = filters;

	const router = useRouter();
	const selection = useReceiptsSelection();

	const updateSearchParams = React.useCallback(
		(newFilters, newSortDir) => {
			const searchParams = new URLSearchParams();

			if (newSortDir === "asc") {
				searchParams.set("sortDir", newSortDir);
			}

			if (newFilters.status) searchParams.set("status", newFilters.status);
			if (newFilters.id) searchParams.set("id", newFilters.id);
			if (newFilters.merchant) searchParams.set("merchant", newFilters.merchant);

			router.push(`${paths.dashboard.receipts}?${searchParams.toString()}`);
		},
		[router]
	);

	const handleClearFilters = React.useCallback(() => {
		updateSearchParams({}, sortDir);
	}, [updateSearchParams, sortDir]);

	const handleStatusChange = React.useCallback(
		(_, value) => {
			updateSearchParams({ ...filters, status: value }, sortDir);
		},
		[updateSearchParams, filters, sortDir]
	);

	const handleMerchantChange = React.useCallback(
		(value) => {
			updateSearchParams({ ...filters, merchant: value }, sortDir);
		},
		[updateSearchParams, filters, sortDir]
	);

	const handleIdChange = React.useCallback(
		(value) => {
			updateSearchParams({ ...filters, id: value }, sortDir);
		},
		[updateSearchParams, filters, sortDir]
	);

	const handleSortChange = React.useCallback(
		(event) => {
			updateSearchParams(filters, event.target.value);
		},
		[updateSearchParams, filters]
	);

	const hasFilters = status || id || merchant;

	const tabs = [
		{ label: "All", value: "", count: statusCounts?.countAll ?? 0 },
		{ label: "Completed", value: "completed", count: statusCounts?.countCompleted ?? 0 },
		{ label: "Pending", value: "pending", count: statusCounts?.countPending ?? 0 },
		{ label: "Processing", value: "processing", count: statusCounts?.countProcessing ?? 0 },
		{ label: "Failed", value: "failed", count: statusCounts?.countFailed ?? 0 },
	];

	return (
		<div>
			<Tabs onChange={handleStatusChange} sx={{ px: 3 }} value={status ?? ""} variant="scrollable">
				{tabs.map((tab) => (
					<Tab
						icon={<Chip label={tab.count} size="small" variant="soft" />}
						iconPosition="end"
						key={tab.value}
						label={tab.label}
						sx={{ minHeight: "auto" }}
						tabIndex={0}
						value={tab.value}
					/>
				))}
			</Tabs>
			<Divider />
			<Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap", p: 2 }}>
				<Stack direction="row" spacing={2} sx={{ alignItems: "center", flex: "1 1 auto", flexWrap: "wrap" }}>
					<FilterButton
						displayValue={id}
						label="Receipt ID"
						onFilterApply={(value) => {
							handleIdChange(value);
						}}
						onFilterDelete={() => {
							handleIdChange();
						}}
						popover={<IdFilterPopover />}
						value={id}
					/>
					<FilterButton
						displayValue={merchant}
						label="Merchant"
						onFilterApply={(value) => {
							handleMerchantChange(value);
						}}
						onFilterDelete={() => {
							handleMerchantChange();
						}}
						popover={<MerchantFilterPopover />}
						value={merchant}
					/>
					{hasFilters ? <Button onClick={handleClearFilters}>Clear filters</Button> : null}
				</Stack>
				{selection.selectedAny ? (
					<Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
						<Typography color="text.secondary" variant="body2">
							{selection.selected.size} selected
						</Typography>
						<Button color="error" variant="contained">
							Delete
						</Button>
					</Stack>
				) : null}
				<Select name="sort" onChange={handleSortChange} sx={{ maxWidth: "100%", width: "120px" }} value={sortDir}>
					<Option value="desc">Newest</Option>
					<Option value="asc">Oldest</Option>
				</Select>
			</Stack>
		</div>
	);
}

function MerchantFilterPopover() {
	const { anchorEl, onApply, onClose, open, value: initialValue } = useFilterContext();
	const [value, setValue] = React.useState("");

	React.useEffect(() => {
		setValue(initialValue ?? "");
	}, [initialValue]);

	return (
		<FilterPopover anchorEl={anchorEl} onClose={onClose} open={open} title="Filter by merchant">
			<FormControl>
				<OutlinedInput
					onChange={(event) => {
						setValue(event.target.value);
					}}
					onKeyUp={(event) => {
						if (event.key === "Enter") {
							onApply(value);
						}
					}}
					value={value}
				/>
			</FormControl>
			<Button
				onClick={() => {
					onApply(value);
				}}
				variant="contained"
			>
				Apply
			</Button>
		</FilterPopover>
	);
}

function IdFilterPopover() {
	const { anchorEl, onApply, onClose, open, value: initialValue } = useFilterContext();
	const [value, setValue] = React.useState("");

	React.useEffect(() => {
		setValue(initialValue ?? "");
	}, [initialValue]);

	return (
		<FilterPopover anchorEl={anchorEl} onClose={onClose} open={open} title="Filter by ID">
			<FormControl>
				<OutlinedInput
					onChange={(event) => {
						setValue(event.target.value);
					}}
					onKeyUp={(event) => {
						if (event.key === "Enter") {
							onApply(value);
						}
					}}
					value={value}
				/>
			</FormControl>
			<Button
				onClick={() => {
					onApply(value);
				}}
				variant="contained"
			>
				Apply
			</Button>
		</FilterPopover>
	);
}
