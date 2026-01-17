import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

type Transaction = {
	id: string;
	date: string;
	description: string;
	category: string;
	amount: number;
	currency?: string;
};

type TransactionsListProps = {
	transactions?: Transaction[];
};

const SAMPLE_TRANSACTIONS: Transaction[] = [
	{ id: "txn-1", date: "2025-10-24", description: "Cloud hosting", category: "Infrastructure", amount: -320.5 },
	{ id: "txn-2", date: "2025-10-23", description: "Team lunch", category: "Operations", amount: -84.75 },
	{ id: "txn-3", date: "2025-10-22", description: "Design software", category: "Software", amount: -129 },
	{ id: "txn-4", date: "2025-10-20", description: "Client refund", category: "Revenue adjustments", amount: 210 },
];

export function TransactionsList({ transactions = SAMPLE_TRANSACTIONS }: TransactionsListProps) {
	return (
		<Card variant="outlined">
			<CardHeader title="Recent Transactions" titleTypographyProps={{ variant: "subtitle1" }} />
			<CardContent>
				<TableContainer sx={{ maxHeight: 320 }}>
					<Table stickyHeader size="small" aria-label="recent transactions">
						<TableHead>
							<TableRow>
								<TableCell>Date</TableCell>
								<TableCell>Description</TableCell>
								<TableCell>Category</TableCell>
								<TableCell align="right">Amount</TableCell>
							</TableRow>
						</TableHead>
						<TableBody>
							{transactions.map((txn) => {
								const currency = txn.currency ?? "USD";
								const formatter = new Intl.NumberFormat(undefined, { style: "currency", currency });
								return (
									<TableRow hover key={txn.id} sx={{ "&:last-of-type td": { borderBottom: 0 } }}>
										<TableCell>
											<Typography variant="body2">{txn.date}</Typography>
										</TableCell>
										<TableCell>
											<Typography variant="body2">{txn.description}</Typography>
										</TableCell>
										<TableCell>
											<Typography variant="body2">{txn.category}</Typography>
										</TableCell>
										<TableCell align="right">
											<Typography color={txn.amount < 0 ? "error.main" : "success.main"} variant="body2">
												{formatter.format(txn.amount)}
											</Typography>
										</TableCell>
									</TableRow>
								);
							})}
						</TableBody>
					</Table>
				</TableContainer>
			</CardContent>
		</Card>
	);
}
