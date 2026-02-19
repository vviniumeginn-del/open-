---
aliases: []
tags: [IP_Brain/02, GEN]
created: 2026-01-29
status: Active
---

# AI图片生成提示词方法论

> [!abstract] 元数据头 (AI Read Only)
> **【文档ID】** DOC-02-GEN-154044
> **【文档标题】** AI图片生成提示词方法论.md
> **【所属模块】** 02_我会什么
> **【适用角色】** 内容教练
> **【核心结论】** ---...
> **【调用触发】** 自动生成
> **【冲突权重】** High

---

## Visual Slicing Protocol v3.3

### [Role Definition]

You actively fight "Horror Vacui" (the fear of empty space) by strictly defining where objects act and where the void exists, while ensuring the space feels physically accurate and "Lived-in."

### [Goal]

Analyze the provided image to reconstruct its 3D Architecture, Industrial Anatomy, and Set Decoration. You must generate a prompt that defines the "Container" first, then the "Content" (Furniture), and crucially the "Soul" (Props/Decor), while explicitly preventing common AI hallucinations.

### The 5-Step Structural Analysis Protocol

#### Step 1: The Architectural Shell (The Box Constraints)

**Logic**: Build the room limits first.

- **The Lid (Ceiling)**: Explicitly define the vertical cap (AC vents/Tray ceiling) to limit height.
- **The Limit (Floor)**: Define material and Rug Coverage % to limit floor depth.
- **The Apertures**: Define the physical "Hole" in the wall (Window/Door frame).

#### Step 2: The Camera Matrix (Optics & Framing)

**Logic**: Fix "Camera Deviation."

- **Focal Length**: Telephoto (50mm-85mm). (Prohibit Wide Angle stretching).
- **The Crop Strategy**: State which objects are cut off by the frame edges. This forces the viewer into the scene.

#### Step 3: Industrial Anatomy (The Structure)

**Logic**: Define how furniture is built.

- **Skeleton**: Describe Industrial Structure (e.g., "Chrome tubular frame," "V-leg solid wood") instead of just brand names.
- **Material**: Describe surface physics (e.g., "Mohair velvet," "Oxidized metal").

#### Step 4: Set Dressing & Gravity (The "Lived-in" Soul)

**Logic**: Fix "Showroom Sterility."

- **The List**: You must extract a specific list of Small Props (Books, Candles, Mugs, Plants).
- **Gravity**: Objects must lean, stack, or drape (e.g., "Art leaning against wall," "Blanket draped").
- **Imperfection**: Describe textures as "Distressed," "Wrinkled," or "Faded."

#### Step 5: Light Vector & Atmosphere (The Physics)

**Logic**: Fix "Lighting Disconnects."

- **Vector**: Light originates from Apertures.
- **Kelvin**: Define warmth (3000K vs 5500K).

### [Output Format: The Structural Prompt]

Please generate the final prompt using this strict template.

**[Header]**:
[Aspect Ratio], [Focal Length: 50mm-85mm], [Framing: Cropped/Close-up], [Depth of Field]

**[The Architecture (The Container)]**:
- Ceiling: [Structure: Tray/Vents/Beams - Defining Height Limit]
- Walls: [Material & Color & Molding details]
- Floor: [Material] + [Rug Coverage % - Defining Horizontal Limit]
- Apertures: [Physical Window/Door Hole Description]

**[The Set Dressing (The Lived-in Details - MANDATORY)]**:
- On Surfaces: [List specific props: e.g., Open books, ceramic mugs, candles]
- On Floor: [List items: e.g., Woven baskets, leaning artworks, stacks]
- Soft Goods: [Texture details: e.g., Wrinkled linen throw, distressed rug, embroidered pillows]

**[Spatial Layout (Anatomy & Crop)]**:
- Foreground (The Anchor): [Item Description] + [Micro-Texture] + [Cropping Logic: Cut by bottom/side edge]
- Midground (The Hero):
  - Item 1: [Industrial Anatomy: Frame + Joints + Material] + [Rigid Anchoring]
  - Item 2: [Industrial Anatomy: Shape + Structure] + [Relationship to Item 1]
- Background: [Item] + [Leaning/Stacking Logic] + [Cropping Logic]

**[Lighting & Atmosphere]**:
[Light Source linking to Apertures], [Kelvin Temperature], [Shadow Quality], [Atmospheric Haze?]

**[Negative Constraints]**:
No wide angle, no infinite ceiling, no empty floor running to infinity, no generic furniture shapes (must define structure), no floating objects, no empty surfaces (must have props).

---

## 镜头抽卡提示词

Analyze the entire composition of the input image. Identify all the key objects present and their spatial relationships/interactions. Generate 4 different shots in the same scene. All frames feature photorealistic textures, consistent cinematic color grading, and reference images generate 4 images from different angles.

---

## 9个镜头生成提示词

分析输入图像的整个构图。识别所有存在的关键主体（无论是单人、群体/情侣、车辆还是特定物体）及其空间关系/互动。

展示在同一环境中完全是这些主体的 9 个不同镜头。

你必须调整标准的电影镜头类型以适应内容（例如，如果是群体，保持群体在一起；如果是物体，构图包含整个物体）：

### 第一组（建立背景）

1. **大远景 (ELS)**：主体在广阔的环境中显得很小。
2. **全景 (LS)**：完整的主体或群体从上到下可见（从头到脚 / 从车轮到车顶）。
3. **中远景 (美式镜头/四分之三)**：构图从膝盖以上（针对人物）或 3/4 视角（针对物体）。

### 第二组（核心覆盖）

4. **中景 (MS)**：构图从腰部以上（或物体的中心核心）。聚焦于互动/动作。
5. **中特写 (MCU)**：构图从胸部以上。主要主体的亲密构图。
6. **特写 (CU)**：紧凑构图于脸部或物体的"正面"。

### 第三组（细节与角度）

7. **大特写 (ECU)**：强烈聚焦于关键特征（眼睛、手、标志、纹理）的微距细节。
8. **低角度镜头 (仰视/虫眼)**：从地面仰望主体（壮观/英雄感）。
9. **高角度镜头 (俯视/鸟瞰)**：从上方俯瞰主体。

### 一致性要求

确保严格的一致性：所有 9 个面板中是相同的人物/物体、相同的衣服和相同的光照。景深应逼真地变化（特写镜头中的背景虚化）。

以全面的焦距范围展示输入图像中的特定主体/场景。所有帧均具有照片般逼真的纹理，一致的电影级调色，以及针对所分析的主体或物体特定数量的正确构图。生成9张图片。