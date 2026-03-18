import { useEffect, useState } from "react";
import {
  AcceptReject,
  ExtractedDataDisplay,
  FilePreview,
  useItemData,
  type Highlight,
  type ExtractedData,
  Button,
} from "@llamaindex/ui";
import { Clock, XCircle, Download } from "lucide-react";
import { useParams } from "react-router-dom";
import { useToolbar } from "@/lib/ToolbarContext";
import { useNavigate } from "react-router-dom";
import { modifyJsonSchema } from "@llamaindex/ui/lib";
import { APP_TITLE } from "@/lib/config";
import { downloadExtractedDataItem } from "@/lib/export";
import { useMetadataContext } from "@/lib/MetadataProvider";
import { convertBoundingBoxesToHighlights } from "@/lib/utils";

export default function ItemPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const { setButtons, setBreadcrumbs } = useToolbar();
  const [highlight, setHighlight] = useState<Highlight | undefined>(undefined);
  const { metadata } = useMetadataContext();

  // Use the hook to fetch item data (initially with a default schema)
  const itemHookData = useItemData<any>({
    // We'll update the schema based on classification once data loads
    jsonSchema: modifyJsonSchema(metadata.schemas["10-K"] || {}, {}),
    itemId: itemId as string,
    isMock: false,
  });

  // Determine the correct schema based on classification
  const classificationData = itemHookData.item?.data as
    | ExtractedData<any>
    | undefined;
  const classification = (
    (classificationData?.metadata?.classification as string | undefined) ||
    "10-K"
  ).toUpperCase();
  const correctSchema =
    metadata.schemas[classification] || metadata.schemas["10-K"];

  // Update the schema in itemHookData if classification is available
  const [schemaKey, setSchemaKey] = useState(0);
  const [appliedSchema, setAppliedSchema] = useState(correctSchema);

  useEffect(() => {
    if (classification && metadata.schemas[classification]) {
      setAppliedSchema(modifyJsonSchema(metadata.schemas[classification], {}));
      setSchemaKey(schemaKey + 1);
    }
  }, [classification, metadata.schemas]);

  const navigate = useNavigate();

  useEffect(() => {
    const extractedData = itemHookData.item?.data as
      | ExtractedData<unknown>
      | undefined;
    const fileName = extractedData?.file_name;
    if (fileName) {
      setBreadcrumbs([
        { label: APP_TITLE, href: "/" },
        {
          label: fileName,
          isCurrentPage: true,
        },
      ]);
    }

    return () => {
      setBreadcrumbs([{ label: APP_TITLE, href: "/" }]);
    };
  }, [itemHookData.item?.data, setBreadcrumbs]);

  useEffect(() => {
    setButtons(() => [
      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (itemData) {
              downloadExtractedDataItem(itemData);
            }
          }}
          disabled={!itemData}
          startIcon={<Download className="h-4 w-4" />}
          label="Export JSON"
        />
        <AcceptReject<any>
          itemData={itemHookData}
          onComplete={() => navigate("/")}
        />
      </div>,
    ]);
    return () => {
      setButtons(() => []);
    };
  }, [itemHookData.data, setButtons]);

  const {
    item: itemData,
    updateData,
    loading: isLoading,
    error,
  } = itemHookData;

  const classificationReasoning = (itemData?.data as ExtractedData<any>)
    ?.metadata?.classification_reasoning as string | undefined;

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
          <div className="text-sm text-gray-500">Loading item...</div>
        </div>
      </div>
    );
  }

  if (error || !itemData) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <div className="text-sm text-gray-500">
            Error loading item: {error || "Item not found"}
          </div>
        </div>
      </div>
    );
  }

  const extractedData = itemData.data as ExtractedData<any>;
  const fileId = extractedData.file_id;

  return (
    <div className="flex h-full bg-gray-50">
      <div className="w-1/2 border-r h-full border-gray-200 bg-white">
        {fileId && (
          <FilePreview
            fileId={fileId}
            onBoundingBoxClick={(box, pageNumber) => {
              console.log("Bounding box clicked:", box, "on page:", pageNumber);
            }}
            highlight={highlight}
          />
        )}
      </div>

      <div className="flex-1 bg-white h-full overflow-y-auto">
        <div className="p-4 space-y-4">
          {/* Classification Info */}
          {classification && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <div className="text-sm font-semibold text-blue-900">
                Document Type: {classification}
              </div>
              {classificationReasoning && (
                <div className="text-xs text-blue-600 mt-1">
                  {classificationReasoning}
                </div>
              )}
            </div>
          )}
          <ExtractedDataDisplay<any>
            key={schemaKey}
            extractedData={extractedData}
            title="Extracted Data"
            onChange={(updatedData) => {
              updateData(updatedData);
            }}
            onHoverField={(args) => {
              const highlights = convertBoundingBoxesToHighlights(
                args?.metadata?.citation,
              );
              setHighlight(highlights[0]);
            }}
            jsonSchema={appliedSchema}
          />
        </div>
      </div>
    </div>
  );
}
