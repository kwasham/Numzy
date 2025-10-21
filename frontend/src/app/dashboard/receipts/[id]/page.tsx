'use client';

import { useState } from "react";
import {
  Box,
  AppBar,
  Toolbar,
  Chip,
  Button,
  IconButton,
  Tabs,
  Tab,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Divider,
  TextField,
  InputAdornment,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  Stack,
} from "@mui/material";
import {
  Check,
  Camera,
  MagnifyingGlass,
  Plus,
  Minus,
  PencilSimple,
  Warning,
  CaretRight,
  ArrowsDownUp,
  DownloadSimple,
  Upload,
  Trash,
  CheckCircle,
  Eye,
} from "@phosphor-icons/react";
import starbucksReceipt from "public/receipts/sample.png";

export default function ReceiptDetailPageOriginal() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#000",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <Box
        sx={{
          width: "100%",
          maxWidth: "1600px",
          display: "flex",
          flexDirection: "column",
          flex: 1,
        }}
      >
        {/* Top Bar */}
        <AppBar
          position="static"
          sx={{
            bgcolor: "#000",
            boxShadow: "none",
            borderBottom: "1px solid #222",
          }}
        >
          <Toolbar sx={{ px: 3 }}>
            {/* Left Spacer - matches left sidebar width */}
            <Box sx={{ width: 280, flexShrink: 0 }} />

            {/* Center - Status Chips */}
            <Box
              sx={{
                width: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1.5,
                flexShrink: 0,
              }}
            >
              <Chip
                icon={<Check size={16} weight="bold" />}
                label="Receipt: Complete"
                sx={{
                  bgcolor: "transparent",
                  border: "1px solid #00ff88",
                  color: "#00ff88",
                  px: 2,
                  py: 1,
                  height: "auto",
                  "& .MuiChip-icon": {
                    color: "#00ff88",
                  },
                }}
              />

              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 0.75,
                  px: 2,
                  py: 1,
                  borderRadius: 2,
                  border: "1px solid #555",
                  bgcolor: "transparent",
                }}
              >
                <Typography variant="body2" sx={{ color: "#fff" }}>
                  Prediction Accuracy: 96.6%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={96.6}
                  sx={{
                    height: 4,
                    width: 128,
                    borderRadius: 2,
                    bgcolor: "#1a1a1a",
                    "& .MuiLinearProgress-bar": {
                      bgcolor: "#00d9ff",
                      borderRadius: 2,
                    },
                  }}
                />
              </Box>
            </Box>

            {/* Right - Actions */}
            <Box
              sx={{
                width: 320,
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                gap: 1.5,
                flexShrink: 0,
              }}
            >
              <IconButton
                sx={{
                  border: "1px solid #555",
                  borderRadius: 2,
                  "&:hover": {
                    bgcolor: "rgba(255,255,255,0.05)",
                  },
                }}
              >
                <Camera size={20} color="#fff" />
              </IconButton>

              <Button
                variant="outlined"
                sx={{
                  borderColor: "#555",
                  color: "#fff",
                  px: 3,
                  py: 1.25,
                  borderRadius: 2,
                  "&:hover": {
                    bgcolor: "rgba(255,255,255,0.05)",
                    borderColor: "#555",
                  },
                }}
              >
                Save
              </Button>

              <Button
                variant="outlined"
                sx={{
                  borderColor: "#555",
                  color: "#fff",
                  px: 3,
                  py: 1.25,
                  borderRadius: 2,
                  "&:hover": {
                    bgcolor: "rgba(255,255,255,0.05)",
                    borderColor: "#555",
                  },
                }}
              >
                Export
              </Button>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Box
          sx={{
            display: "flex",
            flex: 1,
            overflow: "hidden",
            justifyContent: "center",
          }}
        >
          {/* Left Sidebar - Processing Card */}
          <Box
            sx={{
              width: 280,
              borderRight: "1px solid #222",
              bgcolor: "#000",
              p: 3,
              overflowY: "auto",
              flexShrink: 0,
            }}
          >
            {/* Processing Card */}
            <Card
              sx={{
                bgcolor: "#0a0a0a",
                border: "1px solid #333",
                // borderRadius: 4,
                mb: 3,
              }}
            >
              <CardContent>
                <List sx={{ p: 0 }}>
                  {/* Receipt processing - Active */}
                  <ListItem
                    sx={{
                      px: 1.5,
                      py: 1.5,
                      borderRadius: 1,
                      bgcolor: "#111",
                      border: "1px solid #444",
                      mb: 1,
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Check size={18} weight="bold" color="#fff" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Receipt processing"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#fff",
                      }}
                    />
                  </ListItem>

                  {/* Extract data */}
                  <ListItem
                    button
                    sx={{
                      px: 1.5,
                      py: 1.5,
                      borderRadius: 2,
                      mb: 1,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <ArrowsDownUp size={18} color="#999" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Extract data"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#999",
                      }}
                    />
                  </ListItem>

                  {/* Upload receipt */}
                  <ListItem
                    button
                    sx={{
                      px: 1.5,
                      py: 1.5,
                      borderRadius: 2,
                      mb: 1,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Upload size={18} color="#999" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Upload receipt"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#999",
                      }}
                    />
                  </ListItem>

                  {/* Download data */}
                  <ListItem
                    button
                    sx={{
                      px: 1.5,
                      py: 1.5,
                      borderRadius: 2,
                      mb: 1,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <DownloadSimple size={18} color="#999" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Download data"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#999",
                      }}
                    />
                  </ListItem>

                  {/* Delete receipt */}
                  <ListItem
                    button
                    sx={{
                      px: 1.5,
                      py: 1.5,
                      borderRadius: 2,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <Trash size={18} color="#999" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Delete receipt"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#999",
                      }}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>

            {/* Categories Card */}
            <Card
              sx={{
                bgcolor: "#0a0a0a",
                border: "1px solid #333",
                borderRadius: 4,
              }}
            >
              <CardContent>
                <Button
                  fullWidth
                  endIcon={<CaretRight size={16} color="#fff" />}
                  sx={{
                    justifyContent: "space-between",
                    color: "#fff",
                    px: 1.5,
                    py: 1.5,
                    borderRadius: 2,
                    mb: 2,
                    textTransform: "none",
                    "&:hover": {
                      bgcolor: "#111",
                    },
                  }}
                >
                  Categories
                </Button>

                {/* Category Items */}
                <List sx={{ p: 0, mb: 2 }}>
                  <ListItem
                    button
                    sx={{
                      px: 1,
                      py: 1,
                      borderRadius: 2,
                      mb: 1,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Check size={16} weight="bold" color="#00d9ff" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Coffee"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#fff",
                      }}
                    />
                  </ListItem>

                  <ListItem
                    button
                    sx={{
                      px: 1,
                      py: 1,
                      borderRadius: 2,
                      mb: 1,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Check size={16} weight="bold" color="#00d9ff" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Bakery"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#fff",
                      }}
                    />
                  </ListItem>

                  <ListItem
                    button
                    sx={{
                      px: 1,
                      py: 1,
                      borderRadius: 2,
                      "&:hover": {
                        bgcolor: "#111",
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      <Check size={16} weight="bold" color="#00d9ff" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Meals"
                      primaryTypographyProps={{
                        variant: "body2",
                        color: "#fff",
                      }}
                    />
                  </ListItem>
                </List>

                {/* Categories Search */}
                <TextField
                  placeholder="Categories"
                  fullWidth
                  size="small"
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <MagnifyingGlass size={16} color="#999" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      bgcolor: "#111",
                      borderRadius: 2,
                      "& fieldset": {
                        borderColor: "#444",
                      },
                      "&:hover fieldset": {
                        borderColor: "#444",
                      },
                      "&.Mui-focused fieldset": {
                        borderColor: "#00d9ff",
                      },
                    },
                    "& input": {
                      color: "#fff",
                      "&::placeholder": {
                        color: "#666",
                        opacity: 1,
                      },
                    },
                  }}
                />
              </CardContent>
            </Card>
          </Box>

          {/* Center Content */}
          <Box
            sx={{
              width: 600,
              display: "flex",
              flexDirection: "column",
              bgcolor: "#000",
              overflowY: "auto",
              flexShrink: 0,
            }}
          >
            {/* Receipt Viewer Tools */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
                py: 2,
              }}
            >
              <IconButton
                sx={{
                  border: "1px solid #333",
                  borderRadius: 2,
                  bgcolor: "#111",
                  "&:hover": {
                    bgcolor: "#1a1a1a",
                  },
                }}
              >
                <MagnifyingGlass size={20} color="#fff" />
              </IconButton>

              <IconButton
                sx={{
                  border: "1px solid #333",
                  borderRadius: 2,
                  bgcolor: "#111",
                  "&:hover": {
                    bgcolor: "#1a1a1a",
                  },
                }}
              >
                <Plus size={20} color="#fff" />
              </IconButton>

              <IconButton
                sx={{
                  border: "1px solid #333",
                  borderRadius: 2,
                  bgcolor: "#111",
                  "&:hover": {
                    bgcolor: "#1a1a1a",
                  },
                }}
              >
                <Plus size={20} color="#fff" />
              </IconButton>

              <IconButton
                sx={{
                  border: "1px solid #333",
                  borderRadius: 2,
                  bgcolor: "#111",
                  "&:hover": {
                    bgcolor: "#1a1a1a",
                  },
                }}
              >
                <Minus size={20} color="#fff" />
              </IconButton>

              <IconButton
                sx={{
                  border: "1px solid #333",
                  borderRadius: 2,
                  bgcolor: "#111",
                  "&:hover": {
                    bgcolor: "#1a1a1a",
                  },
                }}
              >
                <MagnifyingGlass size={20} color="#fff" />
              </IconButton>

              <Button
                variant="outlined"
                sx={{
                  borderColor: "#333",
                  color: "#fff",
                  px: 2.5,
                  py: 1.25,
                  borderRadius: 2,
                  "&:hover": {
                    bgcolor: "rgba(255,255,255,0.05)",
                    borderColor: "#333",
                  },
                }}
              >
                OVR
              </Button>
            </Box>

            {/* Receipt Image */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                px: 3,
                pb: 3,
              }}
            >
              <Box
                component="img"
                src={starbucksReceipt}
                alt="Starbucks Receipt"
                sx={{
                  maxWidth: 300,
                  maxHeight: 500,
                  objectFit: "contain",
                  border: "1px solid #333",
                  borderRadius: 2,
                  boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
                }}
              />
            </Box>
          </Box>

          {/* Right Sidebar - AI Suggestions */}
          <Box
            sx={{
              width: 320,
              borderLeft: "1px solid #222",
              bgcolor: "#000",
              p: 3,
              overflowY: "auto",
              flexShrink: 0,
            }}
          >
            {/* AI Suggestions Card */}
            <Card
              sx={{
                bgcolor: "#0a0a0a",
                border: "1px solid #333",
                borderRadius: 4,
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, color: "#fff" }}>
                  AI Suggestions
                </Typography>

                <Stack spacing={1.5}>
                  {/* Suggestion 1 */}
                  <Card
                    sx={{
                      bgcolor: "#111",
                      border: "1px solid #444",
                      borderRadius: 3,
                      cursor: "pointer",
                      transition: "border-color 0.2s",
                      "&:hover": {
                        borderColor: "#00d9ff",
                      },
                    }}
                  >
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                      <Typography variant="body2" sx={{ mb: 1, color: "#fff" }}>
                        Apply the Travel category
                      </Typography>
                      <Typography variant="body2" sx={{ color: "#666" }}>
                        Based on expense policy, this qualifies as travel
                      </Typography>
                    </CardContent>
                  </Card>

                  {/* Suggestion 2 */}
                  <Card
                    sx={{
                      bgcolor: "#111",
                      border: "1px solid #444",
                      borderRadius: 3,
                      cursor: "pointer",
                      transition: "border-color 0.2s",
                      "&:hover": {
                        borderColor: "#00d9ff",
                      },
                    }}
                  >
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                      <Typography variant="body2" sx={{ mb: 0.5 }}>
                        <Box component="span" sx={{ color: "#fff" }}>
                          Starbucks
                        </Box>{" "}
                        has been assigned
                      </Typography>
                      <Typography variant="body2">
                        <Box component="span" sx={{ color: "#00d9ff" }}>
                          18 times
                        </Box>{" "}
                        <Box component="span" sx={{ color: "#fff" }}>
                          this month
                        </Box>
                      </Typography>
                    </CardContent>
                  </Card>

                  {/* Suggestion 3 */}
                  <Card
                    sx={{
                      bgcolor: "#111",
                      border: "1px solid #444",
                      borderRadius: 3,
                      cursor: "pointer",
                      transition: "border-color 0.2s",
                      "&:hover": {
                        borderColor: "#00d9ff",
                      },
                    }}
                  >
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                      <Typography variant="body2" sx={{ mb: 1, color: "#fff" }}>
                        This amount is higher than
                      </Typography>
                      <Typography variant="body2" sx={{ color: "#666" }}>
                        your usual average spend
                      </Typography>
                    </CardContent>
                  </Card>
                </Stack>
              </CardContent>
            </Card>

            {/* Audit Trail Card */}
            <Card
              sx={{
                bgcolor: "#0a0a0a",
                border: "1px solid #333",
                borderRadius: 4,
                mt: 3,
              }}
            >
              <CardContent>
                <Typography variant="h6" sx={{ mb: 3, color: "#fff" }}>
                  Audit Trail
                </Typography>

                <Stack spacing={2}>
                  {/* Audit Entry 1 */}
                  <Box sx={{ display: "flex", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: "#111",
                        border: "1px solid #444",
                      }}
                    >
                      <CheckCircle size={16} color="#00ff88" weight="fill" />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body2" sx={{ color: "#fff" }}>
                          Receipt verified
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#666" }}>
                          2m ago
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ color: "#666" }}>
                        Kirk confirmed all fields
                      </Typography>
                    </Box>
                  </Box>

                  {/* Audit Entry 2 */}
                  <Box sx={{ display: "flex", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: "#111",
                        border: "1px solid #444",
                      }}
                    >
                      <Eye size={16} color="#00d9ff" weight="fill" />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body2" sx={{ color: "#fff" }}>
                          Receipt reviewed
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#666" }}>
                          5m ago
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ color: "#666" }}>
                        Kirk viewed the receipt
                      </Typography>
                    </Box>
                  </Box>

                  {/* Audit Entry 3 */}
                  <Box sx={{ display: "flex", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: "#111",
                        border: "1px solid #444",
                      }}
                    >
                      <ArrowsDownUp size={16} color="#00d9ff" weight="bold" />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body2" sx={{ color: "#fff" }}>Data extracted</Typography>
                        <Typography variant="caption" sx={{ color: "#666" }}>
                          8m ago
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ color: "#666" }}>
                        AI extracted 12 fields
                      </Typography>
                    </Box>
                  </Box>

                  {/* Audit Entry 4 */}
                  <Box sx={{ display: "flex", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: "#111",
                        border: "1px solid #444",
                      }}
                    >
                      <Check size={16} color="#00d9ff" weight="bold" />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body2" sx={{ color: "#fff" }}>
                          Processing complete
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#666" }}>
                          10m ago
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ color: "#666" }}>
                        Receipt successfully processed
                      </Typography>
                    </Box>
                  </Box>

                  {/* Audit Entry 5 */}
                  <Box sx={{ display: "flex", gap: 1.5 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: "#111",
                        border: "1px solid #444",
                      }}
                    >
                      <Upload size={16} color="#999" weight="bold" />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body2" sx={{ color: "#fff" }}>
                          Receipt uploaded
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#666" }}>
                          12m ago
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ color: "#666" }}>
                        Kirk uploaded receipt.jpg
                      </Typography>
                    </Box>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Box>
        </Box>

        {/* Tabs Section - Spans Full Width */}
        <Box
          sx={{
            borderTop: "1px solid #222",
            bgcolor: "#000",
          }}
        >
          {/* Tab Headers */}
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            sx={{
              borderBottom: "1px solid #222",
              "& .MuiTab-root": {
                color: "#999",
                textTransform: "none",
                flex: 1,
                py: 2,
                transition: "color 0.2s",
                "&:hover": {
                  color: "#fff",
                },
              },
              "& .Mui-selected": {
                color: "#00d9ff",
              },
              "& .MuiTabs-indicator": {
                bgcolor: "#00d9ff",
                height: 2,
              },
            }}
          >
            <Tab label="Extracted Fields" />
            <Tab label="Line Items" />
            <Tab label="Insights" />
          </Tabs>

          {/* Extracted Fields Cards */}
          {activeTab === 0 && (
            <Box sx={{ display: "flex", gap: 2, p: 3 }}>
              {/* Vendor Card */}
              <Card
                sx={{
                  flex: 1,
                  bgcolor: "#0a0a0a",
                  border: "1px solid #222",
                  borderRadius: 4,
                }}
              >
                <CardContent>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 1.5,
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: "#999",
                        textTransform: "uppercase",
                        letterSpacing: 1.2,
                      }}
                    >
                      Vendor
                    </Typography>
                    <IconButton size="small">
                      <PencilSimple size={18} color="#999" />
                    </IconButton>
                  </Box>

                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 1.5,
                    }}
                  >
                    <Typography variant="h6" sx={{ color: "#fff" }}>Starbucks</Typography>
                    <Typography sx={{ color: "#00d9ff" }}>92%</Typography>
                  </Box>

                  <LinearProgress
                    variant="determinate"
                    value={92}
                    sx={{
                      height: 4,
                      borderRadius: 2,
                      bgcolor: "#222",
                      mb: 1.5,
                      "& .MuiLinearProgress-bar": {
                        bgcolor: "#00d9ff",
                        borderRadius: 2,
                      },
                    }}
                  />

                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                    }}
                  >
                    <LinearProgress
                      variant="determinate"
                      value={9}
                      sx={{
                        flex: 1,
                        height: 4,
                        borderRadius: 2,
                        bgcolor: "#222",
                        "& .MuiLinearProgress-bar": {
                          bgcolor: "#00d9ff",
                          borderRadius: 2,
                        },
                      }}
                    />
                    <Typography variant="caption" sx={{ color: "#999" }}>
                      9%
                    </Typography>
                  </Box>
                </CardContent>
              </Card>

              {/* Date Card */}
              <Card
                sx={{
                  flex: 1,
                  bgcolor: "#0a0a0a",
                  border: "1px solid #222",
                  borderRadius: 4,
                }}
              >
                <CardContent>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 1.5,
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: "#999",
                        textTransform: "uppercase",
                        letterSpacing: 1.2,
                      }}
                    >
                      Date
                    </Typography>
                    <IconButton size="small">
                      <PencilSimple size={18} color="#999" />
                    </IconButton>
                  </Box>

                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 1,
                    }}
                  >
                    <Typography variant="h6" sx={{ color: "#fff" }}>2025-09-27</Typography>
                    <Warning size={20} color="#ff6b9d" weight="fill" />
                  </Box>

                  <Box
                    sx={{
                      height: 4,
                      borderRadius: 2,
                      background:
                        "linear-gradient(90deg, #ff6b9d 0%, #ffaa00 100%)",
                      mb: 2,
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <Box
                      sx={{
                        height: "100%",
                        width: "65%",
                      }}
                    />
                  </Box>

                  <Button
                    fullWidth
                    endIcon={<CaretRight size={16} color="#ff6b9d" />}
                    sx={{
                      justifyContent: "space-between",
                      px: 2,
                      py: 1.25,
                      borderRadius: 2,
                      border: "1px solid #ff6b9d",
                      color: "#ff6b9d",
                      textTransform: "none",
                      "&:hover": {
                        bgcolor: "rgba(255, 107, 157, 0.1)",
                      },
                    }}
                  >
                    Suggestion Review
                  </Button>
                </CardContent>
              </Card>

              {/* Total Card */}
              <Card
                sx={{
                  flex: 1,
                  bgcolor: "#0a0a0a",
                  border: "1px solid #222",
                  borderRadius: 4,
                }}
              >
                <CardContent>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      mb: 1,
                    }}
                  >
                    <Typography variant="h6" sx={{ color: "#fff" }}>Total</Typography>
                    <Typography sx={{ color: "#ffaa00" }}>84%</Typography>
                  </Box>

                  <Typography variant="h4" sx={{ mb: 1.5, color: "#fff" }}>
                    $7.05
                  </Typography>

                  <Box
                    sx={{
                      height: 4,
                      borderRadius: 2,
                      background:
                        "linear-gradient(90deg, #00d9ff 0%, #00ff88 50%, #ffaa00 100%)",
                      mb: 1.5,
                      position: "relative",
                      overflow: "hidden",
                    }}
                  >
                    <Box
                      sx={{
                        height: "100%",
                        width: "84%",
                      }}
                    />
                  </Box>

                  <Stack spacing={1} sx={{ mb: 1.5 }}>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "#999" }}>
                        Subtotal
                      </Typography>
                      <Typography variant="body2" sx={{ color: "#fff" }}>6:60</Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "#999" }}>
                        Tax
                      </Typography>
                      <Typography variant="body2" sx={{ color: "#fff" }}>0:45</Typography>
                    </Box>
                  </Stack>

                  <Divider sx={{ bgcolor: "#222", mb: 1 }} />

                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <Typography sx={{ color: "#fff" }}>Total</Typography>
                    <Typography sx={{ color: "#fff" }}>7,05</Typography>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}
