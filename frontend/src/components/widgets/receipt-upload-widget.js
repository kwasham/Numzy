"use client";

import * as React from "react";
import { useAuth } from "@clerk/nextjs";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { toast } from "sonner";

import { FileDropzone } from "@/components/core/file-dropzone";
import { Previewer } from "@/components/widgets/previewer";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function uploadOne(file, token, attempt = 1) {
	const form = new FormData();
	form.append("file", file);
	const headers = {};
	if (token) headers["Authorization"] = `Bearer ${token}`;
	try {
		const res = await fetch(`${API_URL}/receipts`, { method: "POST", body: form, headers });
		if (!res.ok) {
			const text = await res.text().catch(() => "");
			throw new Error(text || `Upload failed (${res.status})`);
		}
		return res.json();
	} catch (error) {
		// Network / CORS / mixed-content errors surface as TypeError in browsers
		if (attempt === 1 && error instanceof TypeError) {
			console.warn("[upload] network error, retrying once", error);
			await new Promise((r) => setTimeout(r, 300));
			return uploadOne(file, token, attempt + 1);
		}
		if (error instanceof TypeError) {
			throw new TypeError(
				"Network error (CORS / mixed content / server down). Verify API reachable at " +
					`${API_URL} and CORS allows this origin.`
			);
		}
		throw error;
	}
}

export function ReceiptUploadWidget() {
	const { getToken } = useAuth();
	const [files, setFiles] = React.useState([]);
	const [uploading, setUploading] = React.useState(false);

	const onDrop = React.useCallback((accepted) => {
		// Accept images or PDFs, enforce size <= 10MB (aligned with API)
		const filtered = accepted.filter((f) => {
			const isImage = f.type?.startsWith("image/");
			const isPdf = f.type === "application/pdf" || /\.pdf$/i.test(f.name || "");
			return (isImage || isPdf) && f.size <= 10 * 1024 * 1024;
		});
		if (filtered.length !== accepted.length) {
			toast.warning("Only images or PDFs up to 10MB are allowed.");
		}
		setFiles((prev) => [...prev, ...filtered]);
	}, []);

	const removeAt = (idx) => setFiles((prev) => prev.filter((_, i) => i !== idx));
	const clearAll = () => setFiles([]);

	const handleUpload = async () => {
		if (files.length === 0) {
			toast.info("Pick a file first.");
			return;
		}
		setUploading(true);
		try {
			const first = files[0];
			let token = null;
			try {
				token = await getToken?.();
			} catch {
				/* ignore */
			}
			const data = await uploadOne(first, token);
			toast.success(`Uploaded: ${first.name}`);
			// Broadcast new receipt so list view can optimistically insert it
			try {
				if (typeof globalThis !== "undefined" && globalThis.dispatchEvent) {
					globalThis.dispatchEvent(new CustomEvent("receipt:uploaded", { detail: data }));
				}
			} catch {
				/* ignore */
			}
			// Optionally, you could route to a detail page if your app supports it
			clearAll();
			console.log("Upload result", data);
		} catch (error) {
			console.error("[upload] final error", error);
			toast.error(error.message || "Upload failed");
		} finally {
			setUploading(false);
		}
	};

	return (
		<Previewer title="Upload Receipt">
			<Box sx={{ p: 3 }}>
				<Stack spacing={2}>
					<Typography variant="body2" color="text.secondary">
						Select a receipt image or PDF (PNG, JPG, WEBP, PDF; up to 10MB) and upload it to the API.
					</Typography>
					<FileDropzone
						accept={{ "image/*": [], "application/pdf": [] }}
						caption="Max file size is 10 MB"
						onDrop={onDrop}
					/>
					{files.length > 0 && (
						<Stack spacing={1}>
							{files.map((f, i) => (
								<Stack key={`${f.name}-${i}`} direction="row" spacing={2} sx={{ alignItems: "center" }}>
									<Typography sx={{ flex: 1 }} variant="body2">
										{f.name} — {(f.size / 1024).toFixed(1)} KB
									</Typography>
									<Button size="small" onClick={() => removeAt(i)}>
										Remove
									</Button>
								</Stack>
							))}
							<Stack direction="row" spacing={2} sx={{ justifyContent: "flex-end" }}>
								<Button color="secondary" size="small" onClick={clearAll} disabled={uploading}>
									Clear
								</Button>
								<Button variant="contained" size="small" onClick={handleUpload} disabled={uploading}>
									{uploading ? (
										<>
											<CircularProgress size={16} sx={{ mr: 1 }} /> Uploading…
										</>
									) : (
										"Upload"
									)}
								</Button>
							</Stack>
						</Stack>
					)}
				</Stack>
			</Box>
		</Previewer>
	);
}

export default ReceiptUploadWidget;
