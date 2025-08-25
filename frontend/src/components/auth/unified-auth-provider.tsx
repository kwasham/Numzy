"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Auth0Provider } from "@auth0/nextjs-auth0";

import { appConfig } from "@/config/app";
import { AuthStrategy } from "@/lib/auth-strategy";
import { AuthProvider as CognitoProvider } from "@/components/auth/cognito/auth-context";
import { AuthProvider as CustomAuthProvider } from "@/components/auth/custom/auth-context";
import { AuthProvider as SupabaseProvider } from "@/components/auth/supabase/auth-context";

// Dynamically load Clerk only when the strategy is set to CLERK.  This avoids
// bundling Clerk in other builds and ensures the publishable key is present.
const ClerkBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const [ClerkProvider, setClerkProvider] = useState<React.ComponentType<any> | null>(null);
  useEffect(() => {
    if (!publishableKey) {
      console.error("[auth] Missing NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY – Clerk cannot initialise.");
      return;
    }
    let active = true;
    import("@clerk/nextjs")
      .then((mod) => {
        if (active) setClerkProvider(() => mod.ClerkProvider);
      })
      .catch((error) => {
        console.error("[auth] Failed dynamic import of @clerk/nextjs", error);
      });
    return () => {
      active = false;
    };
  }, [publishableKey]);
  if (!publishableKey) {
    // Let the app render; protected routes will still fail gracefully
    return <>{children}</>;
  }
  if (!ClerkProvider) {
    // Optionally render a splash or skeleton while loading Clerk
    return null;
  }
  return <ClerkProvider publishableKey={publishableKey}>{children}</ClerkProvider>;
};

export const UnifiedAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const strategy = appConfig.authStrategy;
  const wrapped = useMemo(() => {
    switch (strategy) {
      case AuthStrategy.AUTH0: {
        return <Auth0Provider>{children}</Auth0Provider>;
      }
      case AuthStrategy.CLERK: {
        return <ClerkBoundary>{children}</ClerkBoundary>;
      }
      case AuthStrategy.COGNITO: {
        return <CognitoProvider>{children}</CognitoProvider>;
      }
      case AuthStrategy.CUSTOM: {
        return <CustomAuthProvider>{children}</CustomAuthProvider>;
      }
      case AuthStrategy.SUPABASE: {
        return <SupabaseProvider>{children}</SupabaseProvider>;
      }
      default: {
        // NONE or unknown strategy: simply render the children unmodified
        return <>{children}</>;
      }
    }
  }, [strategy, children]);
  return wrapped;
};