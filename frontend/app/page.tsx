// Root redirect added to prevent 404 at '/'.
// You can replace this with a marketing landing page later.
import { redirect } from 'next/navigation';

export const metadata = { title: 'Numzy' };

export default function RootRedirect() {
  redirect('/dashboard');
}
