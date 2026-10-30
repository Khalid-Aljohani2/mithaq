"use client";

import { useParams } from "next/navigation";
import { createContext, useContext, type ReactNode } from "react";

import { api, type Contract } from "./api";
import { useResource, type Resource } from "./use-resource";

/**
 * Both demo contracts, loaded once for the whole app. The list endpoint has no
 * contract type, so each full contract is fetched for its government or
 * private badge and for party naming.
 */
type ContractsValue = Resource<Contract[]> & { reload: () => void };

const ContractsContext = createContext<ContractsValue | null>(null);

export function ContractsProvider({ children }: { children: ReactNode }) {
  const resource = useResource(async (signal) => {
    const list = await api.contracts(signal);
    return Promise.all(list.contracts.map((c) => api.contract(c.id, signal)));
  }, []);
  return <ContractsContext value={resource}>{children}</ContractsContext>;
}

export function useContracts(): ContractsValue {
  const value = useContext(ContractsContext);
  if (!value) throw new Error("useContracts must be used inside ContractsProvider");
  return value;
}

/** The contract named in the URL, once loaded. */
export function useCurrentContract(): {
  id: string | null;
  contract: Contract | null;
} {
  const params = useParams<{ contractId?: string }>();
  const id = params.contractId ? decodeURIComponent(params.contractId) : null;
  const { data } = useContracts();
  return { id, contract: data?.find((c) => c.id === id) ?? null };
}
