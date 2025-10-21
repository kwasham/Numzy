"use client";

import { useEffect, useMemo, useState } from "react";
import { Box, Button, Card, CardContent, Chip, IconButton, Stack, TextField, Typography } from "@mui/material";
import { ArrowClockwiseIcon } from "@phosphor-icons/react/dist/ssr/ArrowClockwise";
import { ArrowCounterClockwiseIcon } from "@phosphor-icons/react/dist/ssr/ArrowCounterClockwise";
import { CloudArrowUpIcon } from "@phosphor-icons/react/dist/ssr/CloudArrowUp";
import { DatabaseIcon } from "@phosphor-icons/react/dist/ssr/Database";
import { DownloadSimpleIcon } from "@phosphor-icons/react/dist/ssr/DownloadSimple";
import { PlayIcon } from "@phosphor-icons/react/dist/ssr/Play";
import { SkipForwardIcon } from "@phosphor-icons/react/dist/ssr/SkipForward";
import { SquaresFourIcon } from "@phosphor-icons/react/dist/ssr/SquaresFour";
import { TrashIcon } from "@phosphor-icons/react/dist/ssr/Trash";
import { XIcon } from "@phosphor-icons/react/dist/ssr/X";

import { ReceiptBBoxView } from "@/hooks/use-receipt-details";

export function TopBar({
	status,
	accuracy,
	onReprocess,
	onDelete,
	downloadHref,
	brandName,
}: {
	status: string;
	accuracy: number;
	onReprocess?: () => void;
	onDelete?: () => void;
	downloadHref?: string | null;
	brandName: string;
}) {
	const pct = Math.round(accuracy * 100) / 100;
	return (
		<Box
			sx={{
				bgcolor: "#0B0B0D",
				borderBottom: "1px solid rgba(255,255,255,0.07)",
				px: 3,
				py: 1.2,
				display: "grid",
				gridTemplateColumns: { xs: "1fr", md: "260px 1fr 340px" },
				alignItems: "center",
				gap: 2,
			}}
		>
			<Box sx={{ display: { xs: "none", md: "flex" }, alignItems: "center" }}>
				<Typography variant="h6" fontWeight={800}>
					{brandName}
				</Typography>
			</Box>
			<Box
				sx={{
					display: "flex",
					flexDirection: { xs: "column", md: "row" },
					justifyContent: "center",
					alignItems: "center",
					gap: 4,
				}}
			>
				<Typography variant="body2" sx={{ opacity: 0.9 }}>
					Processing receipt:{" "}
					<Box component="span" sx={{ fontWeight: 600 }}>
						{status}
					</Box>
				</Typography>
				<Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
					<Typography variant="body2" sx={{ opacity: 0.9 }}>
						Prediction Accuracy:{" "}
						<Box component="span" sx={{ fontWeight: 600 }}>
							{pct}%
						</Box>
					</Typography>
					<Box sx={{ width: 160, height: 4, borderRadius: 2, bgcolor: "rgba(255,255,255,0.15)", overflow: "hidden" }}>
						<Box sx={{ height: "100%", width: `${pct}%`, bgcolor: "#6EC1FF" }} />
					</Box>
				</Box>
			</Box>
			<Box sx={{ display: "flex", justifyContent: { xs: "flex-start", md: "flex-end" }, gap: 1 }}>
				<Button
					size="small"
					variant="outlined"
					onClick={onReprocess}
					sx={{ color: "#EDEDED", borderColor: "rgba(255,255,255,0.18)" }}
				>
					Reprocess
				</Button>
				{downloadHref && (
					<Button
						size="small"
						variant="outlined"
						href={downloadHref}
						target="_blank"
						sx={{ color: "#EDEDED", borderColor: "rgba(255,255,255,0.18)" }}
					>
						Download
					</Button>
				)}
				<Button size="small" color="error" variant="outlined" onClick={onDelete}>
					Delete
				</Button>
			</Box>
		</Box>
	);
}

export function ReceiptViewer({
	imageUrl,
	fallbackUrl,
	bboxes,
	activeBboxId,
}: {
	imageUrl: string;
	fallbackUrl?: string;
	bboxes: ReceiptBBoxView[];
	activeBboxId: string | null;
}) {
	const [natural, setNatural] = useState({ w: 0, h: 0 });
	const [container, setContainer] = useState<HTMLDivElement | null>(null);
	const [src, setSrc] = useState(imageUrl);
	const [attemptedFallback, setAttemptedFallback] = useState(false);
	const [loading, setLoading] = useState(true);
	useEffect(() => {
		setSrc(imageUrl);
		setAttemptedFallback(false);
		setLoading(true);
		setNatural({ w: 0, h: 0 });
	}, [imageUrl]);
	const active = useMemo(() => bboxes.find((b) => b.id === activeBboxId) || null, [bboxes, activeBboxId]);
	const overlay = useMemo(() => {
		if (!container || !active || !natural.w || !natural.h) return null;
		const cw = container.clientWidth;
		const ch = container.clientHeight;
		const ratio = natural.w / natural.h;
		const cRatio = cw / ch;
		let iw: number, ih: number;
		if (ratio > cRatio) {
			iw = cw;
			ih = cw / ratio;
		} else {
			ih = ch;
			iw = ch * ratio;
		}
		const ox = (cw - iw) / 2;
		const oy = (ch - ih) / 2;
		return { left: ox + active.x * iw, top: oy + active.y * ih, width: active.w * iw, height: active.h * ih } as const;
	}, [container, active, natural]);
	return (
		<Card
			sx={{
				bgcolor: "#000",
				borderRadius: 2,
				p: 2,
				height: 560,
				width: "100%",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				position: "relative",
			}}
		>
			<Box ref={setContainer} sx={{ position: "relative", width: "100%", height: "100%" }}>
				<Box
					component="img"
					src={src}
					alt="Receipt"
					onLoad={(e) => {
						const img = e.currentTarget as HTMLImageElement;
						setNatural({ w: img.naturalWidth, h: img.naturalHeight });
						setLoading(false);
						if (img.naturalWidth <= 2 && img.naturalHeight <= 2 && fallbackUrl && !attemptedFallback) {
							setAttemptedFallback(true);
							setSrc(fallbackUrl);
							setLoading(true);
						}
					}}
					onError={() => {
						if (fallbackUrl && !attemptedFallback) {
							setAttemptedFallback(true);
							setSrc(fallbackUrl);
						} else {
							setLoading(false);
						}
					}}
					sx={{
						position: "absolute",
						inset: 0,
						m: "auto",
						maxWidth: "100%",
						maxHeight: "100%",
						objectFit: "contain",
						opacity: loading ? 0 : 1,
						transition: "opacity .2s",
					}}
				/>
				{loading && (
					<Box
						sx={{
							position: "absolute",
							inset: 0,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							fontSize: 12,
							color: "#666",
						}}
					>
						Loading preview…
					</Box>
				)}
				{overlay && (
					<Box
						sx={{
							position: "absolute",
							border: "2px solid #C85BFF",
							borderRadius: 1,
							pointerEvents: "none",
							...overlay,
						}}
					/>
				)}
			</Box>
		</Card>
	);
}

export function LeftCategories({
	assigned,
	onChange,
	saving,
	error,
}: {
	assigned: string[];
	onChange?: (c: string[]) => void;
	saving?: boolean;
	error?: string | null;
}) {
	const [input, setInput] = useState("");
	const disableActions = saving || !onChange;
	const add = () => {
		if (disableActions) return;
		const v = input.trim();
		if (!v || assigned.includes(v)) return;
		onChange?.([...assigned, v]);
		setInput("");
	};
	const remove = (c: string) => {
		if (disableActions) return;
		onChange?.(assigned.filter((x) => x !== c));
	};
	return (
		<Card sx={{ bgcolor: "#141418", borderRadius: 2 }}>
			<CardContent sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
				<Typography variant="subtitle1" fontWeight={700}>
					Categories
				</Typography>
				<Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, maxHeight: 180, overflowY: "auto", pr: 0.5 }}>
					{assigned.map((c) => (
						<Stack key={c} direction="row" spacing={1} alignItems="center">
							<Chip
								size="small"
								label={c}
								onDelete={disableActions ? undefined : () => remove(c)}
								sx={{ bgcolor: "#0F0F12", color: "#EDEDED" }}
							/>
						</Stack>
					))}
					{assigned.length === 0 && (
						<Typography variant="body2" sx={{ opacity: 0.6 }}>
							None
						</Typography>
					)}
				</Box>
				<Stack direction="row" spacing={1} sx={{ mt: 1 }}>
					<TextField
						size="small"
						placeholder="Add"
						value={input}
						onChange={(e) => setInput(e.target.value)}
						fullWidth
						variant="outlined"
						InputProps={{ sx: { bgcolor: "#0F0F12", color: "#EDEDED" } }}
					/>
					<Button
						variant="outlined"
						disabled={disableActions || !input.trim()}
						onClick={add}
						sx={{ color: "#EDEDED", borderColor: "rgba(255,255,255,0.18)" }}
					>
						{saving ? "Saving…" : "+"}
					</Button>
				</Stack>
				{error && (
					<Typography variant="caption" sx={{ color: "#ff8080", mt: 0.5 }}>
						{error}
					</Typography>
				)}
			</CardContent>
		</Card>
	);
}

export function ActionNav({
	onReprocess,
	onDelete,
	downloadHref,
	onUpload,
}: {
	onReprocess?: () => void;
	onDelete?: () => void;
	downloadHref?: string | null;
	onUpload?: () => void;
}) {
	return (
		<Card sx={{ bgcolor: "#141418", borderRadius: 2 }}>
			<CardContent sx={{ display: "flex", flexDirection: "column", gap: 1.5, p: 2 }}>
				<Typography variant="subtitle2" sx={{ opacity: 0.7 }}>
					Receipt processing
				</Typography>
				<Button
					size="small"
					startIcon={<DatabaseIcon />}
					onClick={onReprocess}
					sx={{ justifyContent: "flex-start", color: "#EDEDED" }}
					variant="text"
				>
					Extract data
				</Button>
				<Button
					size="small"
					startIcon={<CloudArrowUpIcon />}
					onClick={onUpload}
					sx={{ justifyContent: "flex-start", color: "#EDEDED" }}
					variant="text"
				>
					Upload receipt
				</Button>
				{downloadHref && (
					<Button
						size="small"
						startIcon={<DownloadSimpleIcon />}
						href={downloadHref}
						target="_blank"
						rel="noopener"
						sx={{ justifyContent: "flex-start", color: "#EDEDED" }}
						variant="text"
					>
						Download data
					</Button>
				)}
				<Button
					size="small"
					startIcon={<TrashIcon />}
					onClick={onDelete}
					sx={{ justifyContent: "flex-start", color: "#EDEDED" }}
					variant="text"
				>
					Delete receipt
				</Button>
			</CardContent>
		</Card>
	);
}

export function ImageToolbar({ onPlay, onStep }: { onPlay?: () => void; onStep?: () => void }) {
	return (
		<Card
			sx={{
				bgcolor: "#141418",
				borderRadius: 2,
				p: 1,
				display: "flex",
				alignItems: "center",
				justifyContent: "space-between",
			}}
		>
			<Stack direction="row" spacing={1}>
				<IconButton size="small" onClick={onPlay} sx={{ color: "#EDEDED" }}>
					<PlayIcon />
				</IconButton>
				<IconButton size="small" onClick={onStep} sx={{ color: "#EDEDED" }}>
					<SkipForwardIcon />
				</IconButton>
			</Stack>
			<Stack direction="row" spacing={1}>
				<IconButton size="small" sx={{ color: "#EDEDED" }}>
					<SquaresFourIcon />
				</IconButton>
				<IconButton size="small" sx={{ color: "#EDEDED" }}>
					<ArrowCounterClockwiseIcon />
				</IconButton>
				<IconButton size="small" sx={{ color: "#EDEDED" }}>
					<ArrowClockwiseIcon />
				</IconButton>
				<IconButton size="small" sx={{ color: "#EDEDED" }}>
					<XIcon />
				</IconButton>
			</Stack>
		</Card>
	);
}

export function ExtractedSummaryCard({ store, date, total }: { store: string; date: string; total: string }) {
	return (
		<Card sx={{ bgcolor: "#141418", borderRadius: 2 }}>
			<CardContent sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
				<Typography variant="subtitle1" fontWeight={700}>
					Data extracted
				</Typography>
				<Stack spacing={0.6}>
					<SummaryRow label="Store" value={store} />
					<SummaryRow label="Date" value={date} />
					<SummaryRow label="Total" value={total} />
				</Stack>
			</CardContent>
		</Card>
	);
}

export function LabeledCategoriesCard({ categories }: { categories: string[] }) {
	return (
		<Card sx={{ bgcolor: "#141418", borderRadius: 2 }}>
			<CardContent sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
				<Typography variant="subtitle1" fontWeight={700}>
					File labeled under:
				</Typography>
				<Stack spacing={0.5}>
					{categories.map((c) => (
						<Typography key={c} variant="body2" sx={{ lineHeight: 1.4 }}>
							{c}
						</Typography>
					))}
					{categories.length === 0 && (
						<Typography variant="body2" sx={{ opacity: 0.6 }}>
							None
						</Typography>
					)}
				</Stack>
			</CardContent>
		</Card>
	);
}

export function DataExtractedTable({ store, date, total }: { store: string; date: string; total: string }) {
	return (
		<Card sx={{ bgcolor: "#141418", borderRadius: 2 }}>
			<CardContent sx={{ p: 0 }}>
				<Box sx={{ p: 2 }}>
					<Typography variant="subtitle1" fontWeight={700} gutterBottom>
						Data extracted
					</Typography>
					<Box sx={{ width: "100%", overflowX: "auto" }}>
						<table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
							<thead>
								<tr style={{ textAlign: "left", color: "rgba(255,255,255,0.7)" }}>
									<th style={{ padding: "6px 8px" }}>Store</th>
									<th style={{ padding: "6px 8px" }}>Date</th>
									<th style={{ padding: "6px 8px" }}>Total</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td style={{ padding: "8px 8px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>{store}</td>
									<td style={{ padding: "8px 8px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>{date}</td>
									<td style={{ padding: "8px 8px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>{total}</td>
								</tr>
							</tbody>
						</table>
					</Box>
				</Box>
			</CardContent>
		</Card>
	);
}

function SummaryRow({ label, value }: { label: string; value: string }) {
	return (
		<Stack direction="row" spacing={1}>
			<Typography variant="body2" sx={{ width: 64, color: "rgba(255,255,255,0.6)" }}>
				{label}:
			</Typography>
			<Typography variant="body2" sx={{ fontWeight: 500 }}>
				{value}
			</Typography>
		</Stack>
	);
}
