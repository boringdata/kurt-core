/**
 * Boring UI Component Library
 * A comprehensive, accessible, production-ready UI component library
 */

// Form Components
export { Input } from './Input';
export type { InputProps } from '../types/input';

export { Select } from './Select';
export type { SelectProps, SelectOption, SelectGroup } from '../types/select';

export { Textarea } from './Textarea';
export type { TextareaProps } from '../types/textarea';

export { Checkbox, CheckboxGroup } from './Checkbox';
export type { CheckboxProps, CheckboxGroupProps } from '../types/checkbox';

export { Radio, RadioGroup } from './Radio';
export type { RadioProps, RadioGroupProps } from '../types/checkbox';

export {
  FormGroup,
  FormLayout,
  ValidationMessage,
  FormSection,
} from './Form';
export type {
  FormGroupProps,
  FormLayoutProps,
  ValidationMessageProps,
} from '../types/form';
