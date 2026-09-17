"use client";

import {
  CheckCircle2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

type Farm = {
  id: string;
  name: string;
};

type FoodCategory = {
  code: string;
  name: string;
};

type OfferItemForm = {
  id: number;
  foodCategoryCode: string;
  pounds: string;
};

type CreatedOffer = {
  id: string;
  farm_name: string;
  total_pounds: number;
};

type RecordIntakeDialogProps = {
  onOfferCreated?: () => void;
};

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const fieldClass =
  "h-[42px] w-full rounded-[15px] bg-[#ececec] px-4 text-[16px] " +
  "text-[#343434] outline-none placeholder:text-[#7b7b7b] " +
  "focus:ring-2 focus:ring-[#202020]/20 disabled:cursor-not-allowed " +
  "disabled:opacity-60";

let nextItemId = 1;

function createEmptyItem(): OfferItemForm {
  return {
    id: nextItemId++,
    foodCategoryCode: "",
    pounds: "",
  };
}

function currentLocalDateTime(): string {
  const now = new Date();
  const timezoneOffset = now.getTimezoneOffset() * 60_000;

  return new Date(now.getTime() - timezoneOffset)
    .toISOString()
    .slice(0, 16);
}

function getErrorMessage(payload: unknown): string {
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("detail" in payload)
  ) {
    return "The donation offer could not be recorded.";
  }

  const detail = payload.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (
    typeof detail === "object" &&
    detail !== null &&
    "message" in detail &&
    typeof detail.message === "string"
  ) {
    return detail.message;
  }

  return "The donation offer could not be recorded.";
}

export function RecordIntakeDialog({
  onOfferCreated,
}: RecordIntakeDialogProps) {
  const [open, setOpen] = useState(false);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [categories, setCategories] = useState<FoodCategory[]>([]);
  const [farmId, setFarmId] = useState("");
  const [availableFrom, setAvailableFrom] = useState(
    currentLocalDateTime,
  );
  const [pickupBy, setPickupBy] = useState("");
  const [items, setItems] = useState<OfferItemForm[]>([
    createEmptyItem(),
  ]);
  const [notes, setNotes] = useState("");
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [createdOffer, setCreatedOffer] =
    useState<CreatedOffer | null>(null);

  const selectedCategoryCodes = useMemo(
    () =>
      new Set(
        items
          .map((item) => item.foodCategoryCode)
          .filter(Boolean),
      ),
    [items],
  );

  const unusedCategories = categories.filter(
    (category) => !selectedCategoryCodes.has(category.code),
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    const controller = new AbortController();

    async function loadOptions() {
      setLoadingOptions(true);
      setError("");

      try {
        const [farmsResponse, categoriesResponse] =
          await Promise.all([
            fetch(`${apiUrl}/api/v1/farms`, {
              signal: controller.signal,
              cache: "no-store",
            }),
            fetch(`${apiUrl}/api/v1/food-categories`, {
              signal: controller.signal,
              cache: "no-store",
            }),
          ]);

        if (!farmsResponse.ok || !categoriesResponse.ok) {
          throw new Error("Unable to load intake options.");
        }

        const loadedFarms =
          (await farmsResponse.json()) as Farm[];
        const loadedCategories =
          (await categoriesResponse.json()) as FoodCategory[];

        setFarms(loadedFarms);
        setCategories(loadedCategories);

        setFarmId((currentFarmId) => {
          return currentFarmId || loadedFarms[0]?.id || "";
        });

        setItems((currentItems) =>
          currentItems.map((item, index) => {
            if (
              index === 0 &&
              !item.foodCategoryCode &&
              loadedCategories[0]
            ) {
              return {
                ...item,
                foodCategoryCode: loadedCategories[0].code,
              };
            }

            return item;
          }),
        );
      } catch (requestError: unknown) {
        if (
          requestError instanceof DOMException &&
          requestError.name === "AbortError"
        ) {
          return;
        }

        setError(
          "Could not load donors and food categories. " +
            "Confirm that the backend is running.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setLoadingOptions(false);
        }
      }
    }

    void loadOptions();

    return () => controller.abort();
  }, [open]);

  function resetForm() {
    setFarmId("");
    setAvailableFrom(currentLocalDateTime());
    setPickupBy("");
    setItems([createEmptyItem()]);
    setNotes("");
    setError("");
    setCreatedOffer(null);
  }

  function closeDialog() {
    if (submitting) {
      return;
    }

    setOpen(false);
    resetForm();
  }

  function updateItem(
    itemId: number,
    changes: Partial<OfferItemForm>,
  ) {
    setItems((currentItems) =>
      currentItems.map((item) =>
        item.id === itemId
          ? {
              ...item,
              ...changes,
            }
          : item,
      ),
    );
  }

  function addItem() {
    const nextCategory = unusedCategories[0];

    if (!nextCategory) {
      return;
    }

    setItems((currentItems) => [
      ...currentItems,
      {
        id: nextItemId++,
        foodCategoryCode: nextCategory.code,
        pounds: "",
      },
    ]);
  }

  function removeItem(itemId: number) {
    if (items.length === 1) {
      return;
    }

    setItems((currentItems) =>
      currentItems.filter((item) => item.id !== itemId),
    );
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setError("");

    if (!farmId) {
      setError("Select a distributor.");
      return;
    }

    if (!availableFrom) {
      setError("Enter when the food is available.");
      return;
    }

    const normalizedItems = items.map((item) => ({
      food_category_code: item.foodCategoryCode,
      pounds: Number(item.pounds),
    }));

    if (
      normalizedItems.some(
        (item) =>
          !item.food_category_code ||
          !Number.isFinite(item.pounds) ||
          item.pounds <= 0,
      )
    ) {
      setError(
        "Every food type must have a positive pound amount.",
      );
      return;
    }

    const categoryCodes = normalizedItems.map(
      (item) => item.food_category_code,
    );

    if (categoryCodes.length !== new Set(categoryCodes).size) {
      setError("Each food category can only be entered once.");
      return;
    }

    const availableFromDate = new Date(availableFrom);
    const pickupByDate = pickupBy ? new Date(pickupBy) : null;

    if (
      pickupByDate &&
      pickupByDate.getTime() < availableFromDate.getTime()
    ) {
      setError(
        "The pickup deadline cannot be earlier than the " +
          "available time.",
      );
      return;
    }

    setSubmitting(true);

    try {
      const response = await fetch(
        `${apiUrl}/api/v1/donation-offers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            farm_id: farmId,
            available_from: availableFromDate.toISOString(),
            pickup_by: pickupByDate?.toISOString() ?? null,
            notes: notes.trim() || null,
            items: normalizedItems,
          }),
        },
      );

      const payload: unknown = await response.json();

      if (!response.ok) {
        throw new Error(getErrorMessage(payload));
      }

      setCreatedOffer(payload as CreatedOffer);
      onOfferCreated?.();
    } catch (requestError: unknown) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The donation offer could not be recorded.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-full bg-[#202020] px-[13px] py-[7px] text-[14px] text-white transition hover:bg-black"
      >
        + Record Donation Offer
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeDialog();
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="record-intake-title"
            className="max-h-[calc(100vh-32px)] w-full max-w-[760px] overflow-y-auto rounded-[25px] bg-white px-7 py-8 text-black shadow-xl sm:px-[43px] sm:py-[39px]"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2
                  id="record-intake-title"
                  className="text-[30px] font-normal leading-tight"
                >
                  Record Donation Offer
                </h2>
                <p className="mt-2 text-[15px] text-[#666]">
                  Enter the food reported during the morning call.
                </p>
              </div>

              <button
                type="button"
                aria-label="Close"
                onClick={closeDialog}
                className="shrink-0 text-[#979797] transition hover:text-black"
              >
                <X className="h-8 w-8" strokeWidth={2.5} />
              </button>
            </div>

            {createdOffer ? (
              <div className="py-12 text-center">
                <CheckCircle2 className="mx-auto h-14 w-14 text-green-700" />

                <h3 className="mt-5 text-[24px]">
                  Donation offer recorded
                </h3>

                <p className="mt-3 text-[16px] text-[#555]">
                  {createdOffer.total_pounds.toLocaleString()} lbs
                  from {createdOffer.farm_name}
                </p>

                <button
                  type="button"
                  onClick={closeDialog}
                  className="mt-8 h-[46px] rounded-[20px] bg-[#1e1e1e] px-8 text-[18px] text-white transition hover:bg-black"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <div className="mt-9 grid gap-6 sm:grid-cols-2">
                  <label className="block text-[18px] font-medium">
                    Distributor *
                    <select
                      required
                      value={farmId}
                      disabled={loadingOptions}
                      onChange={(event) =>
                        setFarmId(event.target.value)
                      }
                      className={`${fieldClass} mt-3`}
                    >
                      <option value="">Select a distributor</option>

                      {farms.map((farm) => (
                        <option key={farm.id} value={farm.id}>
                          {farm.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="block text-[18px] font-medium">
                    Available From *
                    <input
                      required
                      type="datetime-local"
                      value={availableFrom}
                      onChange={(event) =>
                        setAvailableFrom(event.target.value)
                      }
                      className={`${fieldClass} mt-3`}
                    />
                  </label>

                  <label className="block text-[18px] font-medium sm:col-span-2">
                    Pickup Deadline
                    <input
                      type="datetime-local"
                      value={pickupBy}
                      onChange={(event) =>
                        setPickupBy(event.target.value)
                      }
                      className={`${fieldClass} mt-3`}
                    />
                  </label>
                </div>

                <fieldset className="mt-8 border-0 p-0">
                  <legend className="text-[20px] font-medium">
                    Food Available *
                  </legend>

                  <div className="mt-4 space-y-4">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className="grid gap-3 sm:grid-cols-[1.4fr_1fr_auto]"
                      >
                        <select
                          required
                          aria-label="Food type"
                          value={item.foodCategoryCode}
                          disabled={loadingOptions}
                          onChange={(event) =>
                            updateItem(item.id, {
                              foodCategoryCode:
                                event.target.value,
                            })
                          }
                          className={fieldClass}
                        >
                          <option value="">
                            Select food type
                          </option>

                          {categories.map((category) => (
                            <option
                              key={category.code}
                              value={category.code}
                              disabled={
                                category.code !==
                                  item.foodCategoryCode &&
                                selectedCategoryCodes.has(
                                  category.code,
                                )
                              }
                            >
                              {category.name}
                            </option>
                          ))}
                        </select>

                        <div className="relative">
                          <input
                            required
                            type="number"
                            min="0.01"
                            step="0.01"
                            inputMode="decimal"
                            aria-label="Pounds"
                            placeholder="Amount"
                            value={item.pounds}
                            onChange={(event) =>
                              updateItem(item.id, {
                                pounds: event.target.value,
                              })
                            }
                            className={`${fieldClass} pr-14`}
                          />

                          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-[14px] text-[#666]">
                            lbs
                          </span>
                        </div>

                        <button
                          type="button"
                          aria-label="Remove food type"
                          disabled={items.length === 1}
                          onClick={() => removeItem(item.id)}
                          className="flex h-[42px] w-[42px] items-center justify-center rounded-[15px] bg-[#ececec] text-[#666] transition hover:bg-[#ddd] disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>

                  <button
                    type="button"
                    disabled={
                      unusedCategories.length === 0 ||
                      loadingOptions
                    }
                    onClick={addItem}
                    className="mt-4 inline-flex items-center gap-2 rounded-[15px] bg-[#ececec] px-5 py-[9px] text-[15px] text-[#555] transition hover:bg-[#ddd] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Plus className="h-4 w-4" />
                    Add Food Type
                  </button>
                </fieldset>

                <label className="mt-8 block text-[18px] font-medium">
                  Notes
                  <textarea
                    maxLength={2000}
                    value={notes}
                    onChange={(event) =>
                      setNotes(event.target.value)
                    }
                    placeholder="Pickup instructions or other details"
                    className="mt-3 block h-[100px] w-full resize-none rounded-[15px] bg-[#ececec] p-4 text-[16px] outline-none focus:ring-2 focus:ring-[#202020]/20"
                  />
                </label>

                {error && (
                  <p
                    role="alert"
                    className="mt-5 rounded-[12px] bg-red-50 px-4 py-3 text-[14px] text-red-800"
                  >
                    {error}
                  </p>
                )}

                <div className="mt-8 flex justify-end gap-4">
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={closeDialog}
                    className="h-[46px] rounded-[20px] bg-[#979797] px-8 text-[18px] text-white transition hover:bg-[#777] disabled:opacity-60"
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    disabled={
                      submitting ||
                      loadingOptions ||
                      farms.length === 0 ||
                      categories.length === 0
                    }
                    className="h-[46px] rounded-[20px] bg-[#1e1e1e] px-8 text-[18px] text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submitting
                      ? "Recording..."
                      : "Submit"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      )}
    </>
  );
}
