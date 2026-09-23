export type Recipient = {
  id: string;
  name: string;
  priority: number;
  is_active: boolean;
  is_fallback: boolean;
  capacity_level: number | null;
  food_type: string[];
};