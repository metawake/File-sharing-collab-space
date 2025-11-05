import type { AppProps } from 'next/app';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../utils/queryClient';
import '../styles/globals.css';
import { ToastProvider } from '../components/ToastProvider';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <Component {...pageProps} />
      </ToastProvider>
    </QueryClientProvider>
  );
}

