import { useCallback, useState } from 'react';

export type FormErrors<TFields extends string> = Partial<Record<TFields, string>>;
export type FormTouched<TFields extends string> = Partial<Record<TFields, boolean>>;

type Validator<TValues> = (values: TValues) => FormErrors<keyof TValues & string>;

/**
 * Tiny form-state helper for forms that don't justify a full library.
 *
 * Tracks per-field error and touched state. `validate(values)` runs the
 * supplied validator and stores any errors. `markTouched(name)` flips a
 * field to touched (call from `onBlur`). `errorFor(name)` returns the
 * error only when the field has been touched, so we don't yell at the
 * user mid-typing.
 */
export const useFormErrors = <TValues extends object>(validate: Validator<TValues>) => {
  type FieldName = keyof TValues & string;
  const [errors, setErrors] = useState<FormErrors<FieldName>>({});
  const [touched, setTouched] = useState<FormTouched<FieldName>>({});

  const validateAll = useCallback(
    (values: TValues): boolean => {
      const next = validate(values);
      setErrors(next);
      // Mark every field with an error as touched so the UI surfaces them.
      const allTouched: FormTouched<FieldName> = {};
      (Object.keys(next) as FieldName[]).forEach((k) => {
        allTouched[k] = true;
      });
      setTouched((prev) => ({ ...prev, ...allTouched }));
      return Object.keys(next).length === 0;
    },
    [validate],
  );

  const validateField = useCallback(
    (values: TValues, name: FieldName) => {
      const next = validate(values);
      setErrors((prev) => ({ ...prev, [name]: next[name] }));
    },
    [validate],
  );

  const markTouched = useCallback((name: FieldName) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
  }, []);

  const errorFor = useCallback(
    (name: FieldName): string | undefined => (touched[name] ? errors[name] : undefined),
    [errors, touched],
  );

  const focusFirstError = useCallback(() => {
    const firstField = (Object.keys(errors) as FieldName[]).find((k) => errors[k]);
    if (!firstField) return;
    const el = document.querySelector<HTMLElement>(`[name="${firstField}"], #${firstField}`);
    el?.focus();
  }, [errors]);

  return { errors, touched, validateAll, validateField, markTouched, errorFor, focusFirstError };
};
