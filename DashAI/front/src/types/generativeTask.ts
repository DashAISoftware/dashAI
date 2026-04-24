export type GenerativeInputType = "str" | "Image" | "Audio" | "Video" | string;
export type CardinalityRange = { min: number; max: number | "n" };
export type Cardinality = number | "n" | CardinalityRange;
export type CardinalityMap = Partial<Record<GenerativeInputType, Cardinality>>;

export interface IGenerativeTask {
  name: string;
  type: string;
  configurable_object: boolean;
  schema: any | null;
  metadata: {
    inputs: CardinalityMap;
    outputs: CardinalityMap;
  };
  description: string;
  display_name: string;
  color: string | null;
}
